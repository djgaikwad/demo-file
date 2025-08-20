import streamlit as st
import pdfplumber
import pandas as pd
import json
import io
import re
from dotenv import load_dotenv
import os
# from langchain_community.llms import Ollama
from PIL import Image

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.llms import Ollama

# Load env vars
load_dotenv()
os.environ['LANGCHAIN_API_KEY'] = os.getenv('LANGCHAIN_API_KEY')

# ----------------- Helper Functions -----------------

def extract_selected_pages(pdf_file, page_numbers):
    """Extract and clean text from selected pages"""
    extracted_text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page_num in page_numbers:
            page = pdf.pages[page_num - 1]
            text = page.extract_text()
            if text:
                cleaned_text = "\n".join([line for line in text.splitlines() if not re.match(r'^\d+$', line)])
                extracted_text += cleaned_text + "\n"
    return extracted_text

def excel_to_json(uploaded_excel):
    """Convert Excel examples to JSON list"""
    df = pd.read_excel(uploaded_excel)
    return df.to_dict(orient="records")

def save_json_to_excel(json_data):
    """Convert JSON to Excel buffer"""
    df_out = pd.DataFrame(json_data)
    buffer = io.BytesIO()
    df_out.to_excel(buffer, index=False)
    buffer.seek(0)
    return buffer

def show_pdf_preview(pdf_file, page_numbers, scale=2):
    """Render selected PDF pages as images"""
    previews = []
    with pdfplumber.open(pdf_file) as pdf:
        for page_num in page_numbers:
            page = pdf.pages[page_num - 1]
            img = page.to_image(resolution=150).original
            # Optionally resize
            w, h = img.size
            img = img.resize((w*scale//2, h*scale//2))
            previews.append(img)
    return previews

# ----------------- Streamlit UI -----------------

st.title("📄 BRD → Test Case Generator (Llama2 Local with Preview)")

# Upload BRD PDF
pdf_file = st.file_uploader("Upload BRD (PDF)", type=["pdf"])
# Upload Example Excel
excel_file = st.file_uploader("Upload Example Test Cases (Excel)", type=["xlsx"])

if pdf_file:
    with pdfplumber.open(pdf_file) as pdf:
        total_pages = len(pdf.pages)
        st.write(f"📑 PDF has **{total_pages}** pages")

    # Default = all pages selected
    selected_pages = st.multiselect(
        "Select Pages to Extract",
        options=list(range(1, total_pages + 1)),
        default=list(range(1, total_pages + 1))
    )

    if selected_pages:
        # Show visual preview of selected pages
        st.subheader("👀 Preview of Selected Pages")
        previews = show_pdf_preview(pdf_file, selected_pages)
        for idx, img in enumerate(previews):
            st.image(img, caption=f"Page {selected_pages[idx]}", use_container_width=True)

        # Extract text
        brd_text = extract_selected_pages(pdf_file, selected_pages)

        # Prepare examples if uploaded
        examples_json = []
        if excel_file:
            examples_json = excel_to_json(excel_file)

        # Prompt Template
        prompt = ChatPromptTemplate(
            [
                ("system", "You are a QA Test Case Generator. Generate test cases in JSON."),
                ("user", f"""
Generate test cases from the given BRD content.
Each test case must include: Scenario, Content, TC_Name, Description.
Examples (if any):
{json.dumps(examples_json, indent=2)}

BRD Content:
{brd_text}
""")
            ]
        )

        # LLM (local llama2 via Ollama)
        # llm = Ollama(model="llama2")
        # Intialize the llm model
        from langchain_groq import ChatGroq

        llm = ChatGroq(model="llama-3.3-70b-verssatile")
        output_parser = StrOutputParser()
        chain = prompt | llm | output_parser

        if st.button("Generate Test Cases"):
            with st.spinner("Generating test cases with Llama2..."):
                response = chain.invoke({})
                response = response.split("```json")[1].split("```")[0].strip()

                try:
                    test_cases = json.loads(response)
                except:
                    st.error("⚠️ LLM output is not valid JSON. Please check formatting.")
                    st.text_area("Raw LLM Output", response, height=300)
                    test_cases = []

                if test_cases:
                    st.success("✅ Test Cases Generated Successfully")
                    st.json(test_cases)

                    # Download JSON
                    st.download_button(
                        "Download JSON",
                        data=json.dumps(test_cases, indent=2),
                        file_name="test_cases.json",
                        mime="application/json"
                    )

                    # Download Excel
                    buffer = save_json_to_excel(test_cases)
                    st.download_button(
                        "Download Excel",
                        data=buffer,
                        file_name="test_cases.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
