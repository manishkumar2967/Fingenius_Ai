import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from database import db
from database.expense_models import CATEGORIES
from analytics.expense_analysis import frame, metrics
from tools.finance_tools import add_expense, update_expense, delete_expense, parse_natural_expense
from rag.document_loader import extract_pdf, chunks
from rag.vector_store import FinancialKnowledgeStore, starter_knowledge
from graph.workflow import build_workflow

st.set_page_config(page_title="FinGenius",page_icon="◆",layout="wide")
st.markdown("""<style>.stApp{background:#09151b;color:#e8f2f0}.hero{padding:1.3rem 0}.hero h1{font-size:3rem;margin:0;color:#5ee6c3}.card{background:#10242c;border:1px solid #24414b;border-radius:14px;padding:1rem}.stMetric{background:#10242c;padding:.6rem;border-radius:12px}</style>""",unsafe_allow_html=True)
db.initialize()
if "store" not in st.session_state: st.session_state.store=FinancialKnowledgeStore(starter_knowledge())
if "chat" not in st.session_state: st.session_state.chat=[]

with st.sidebar:
    st.title("◆ FinGenius")
    view=st.radio("Navigation",["Overview","Expense Manager","Budgets","AI Advisor","Knowledge Base"])
    st.caption("Educational personal-finance support—not professional financial advice.")

records=db.all_expenses(); budget_map=db.budgets(); report=metrics(records,budget_map)
st.markdown("<div class='hero'><h1>Your money, made intelligible.</h1><p>Track spending, set boundaries, and get grounded AI insights.</p></div>",unsafe_allow_html=True)

if view=="Overview":
    a,b,c=st.columns(3); a.metric("All-time spending",f"₹{report['total']:,.2f}"); b.metric("This month",f"₹{report['month']:,.2f}"); c.metric("Average daily",f"₹{report['average_daily']:,.2f}")
    if records:
        left,right=st.columns(2); df=frame(records)
        with left:
            cat=report["category"].reset_index(); cat.columns=["category","amount"]
            if not cat.empty: st.plotly_chart(px.pie(cat,values="amount",names="category",title="This month by category",hole=.45),use_container_width=True)
        with right:
            monthly=df.assign(month=df.expense_date.dt.to_period("M").astype(str)).groupby("month").amount.sum().reset_index()
            st.plotly_chart(px.bar(monthly,x="month",y="amount",title="Monthly spending trend",color_discrete_sequence=["#5ee6c3"]),use_container_width=True)
        st.subheader("Budget alerts")
        if report["budget_usage"]:
            for r in report["budget_usage"]:
                st.progress(min(r["percent"],100)/100,text=f"{r['category']}: ₹{r['spent']:,.0f} / ₹{r['limit']:,.0f} ({r['percent']:.0f}%)")
                if r["percent"]>=100: st.error(f"{r['category']} budget exceeded.")
                elif r["percent"]>=80: st.warning(f"{r['category']} is approaching its budget.")
    else: st.info("Start in Expense Manager to add your first transaction.")

elif view=="Expense Manager":
    st.header("Expense Manager")
    tab1,tab2,tab3=st.tabs(["Add expense","Natural language entry","History & edit"])
    with tab1:
        with st.form("add"):
            col1,col2=st.columns(2); amount=col1.number_input("Amount (₹)",min_value=.01,step=10.0); category=col2.selectbox("Category",CATEGORIES); description=st.text_input("Description"); expense_date=st.date_input("Date",date.today())
            if st.form_submit_button("Save expense",type="primary"):
                try: add_expense(amount,category,description or category,str(expense_date)); st.success("Expense saved."); st.rerun()
                except Exception as e: st.error(str(e))
    with tab2:
        text=st.text_input("Describe an expense",placeholder="I spent 250 rupees on lunch")
        if st.button("Interpret expense") and text:
            try: st.session_state.pending=parse_natural_expense(text); st.success("Expense interpreted. Confirm below before saving.")
            except ValueError as e: st.error(str(e))
        if "pending" in st.session_state:
            p=st.session_state.pending; st.write(f"**₹{p.amount:.2f}** · {p.category} · {p.description}")
            if st.button("Confirm and save interpreted expense",type="primary"):
                try: add_expense(p.amount,p.category,p.description,p.date); del st.session_state.pending; st.success("Saved."); st.rerun()
                except Exception as e: st.error(str(e))
    with tab3:
        if records:
            show=pd.DataFrame(records); st.dataframe(show[["id","expense_date","amount","category","description"]],use_container_width=True,hide_index=True)
            item=st.selectbox("Select expense ID to edit or delete",show.id.tolist())
            current=next(x for x in records if x["id"]==item)
            with st.form("edit"):
                amount=st.number_input("Edit amount",min_value=.01,value=float(current["amount"])); cat=st.selectbox("Edit category",CATEGORIES,index=CATEGORIES.index(current["category"])); desc=st.text_input("Edit description",current["description"]); dt=st.date_input("Edit date",pd.to_datetime(current["expense_date"]).date())
                if st.form_submit_button("Update expense"):
                    try: update_expense(item,amount,cat,desc,str(dt)); st.success("Updated."); st.rerun()
                    except Exception as e: st.error(str(e))
            confirmed=st.checkbox("I confirm that I want to permanently delete this expense.")
            if st.button("Delete selected expense",disabled=not confirmed):
                try: delete_expense(item); st.success("Deleted."); st.rerun()
                except Exception as e: st.error(str(e))
        else: st.info("No expenses saved yet.")

elif view=="Budgets":
    st.header("Budget Management")
    with st.form("budget"):
        col1,col2=st.columns(2); category=col1.selectbox("Category",CATEGORIES); limit=col2.number_input("Monthly limit (₹)",min_value=1.0,step=100.0)
        if st.form_submit_button("Save category limit",type="primary"): db.set_budget(category,limit); st.success("Budget saved."); st.rerun()
    st.subheader("Active limits")
    if budget_map: st.dataframe(pd.DataFrame([{"category":k,"monthly limit":v} for k,v in budget_map.items()]),hide_index=True,use_container_width=True)
    else: st.info("No category limits yet.")

elif view=="AI Advisor":
    st.header("AI Financial Advisor")
    st.caption("Calculations use your SQLite transactions; recommendations are grounded in those results.")
    for q,a in st.session_state.chat[-6:]:
        with st.chat_message("user"): st.write(q)
        with st.chat_message("assistant"): st.markdown(a)
    q=st.chat_input("e.g., Where am I spending the most? How can I reduce costs?")
    if q:
        with st.chat_message("user"): st.write(q)
        with st.chat_message("assistant"):
            try:
                with st.spinner("LangGraph is selecting tools and preparing evidence…"):
                    result=build_workflow().invoke({"query":q,"store":st.session_state.store})
                st.markdown(result["answer"]); st.session_state.chat.append((q,result["answer"]))
            except Exception as e: st.error("AI request failed. Check .env API settings. Details: "+str(e))

elif view=="Knowledge Base":
    st.header("Financial Knowledge Base")
    st.write("The built-in literacy guide is embedded in FAISS. Add financial PDFs to enrich the retrieval knowledge base.")
    uploads=st.file_uploader("Upload educational finance PDFs",type="pdf",accept_multiple_files=True)
    if st.button("Index PDFs") and uploads:
        try:
            docs=starter_knowledge()+[d for f in uploads for d in extract_pdf(f)]
            st.session_state.store=FinancialKnowledgeStore(chunks(docs)); st.success(f"Indexed {len(uploads)} PDFs plus the built-in guide.")
        except Exception as e: st.error(str(e))
    question=st.text_input("Ask a financial-literacy question",placeholder="What is the 50/30/20 rule?")
    if st.button("Search knowledge base") and question:
        hits=st.session_state.store.search(question)
        for (text,source),score in hits: st.markdown(f"**{source}** · relevance {score:.2f}\n\n{text}")
