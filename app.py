import streamlit as st
import os
import re
import pandas as pd
from PIL import Image
import pytesseract
from docx import Document
import pdfplumber
import google.generativeai as genai

# ------------------ Streamlit Setup ------------------
st.set_page_config(page_title="AIEval - DTU Assignment Evaluator", layout="wide")
st.title("AIEval - DTU Assignment Evaluator")
st.caption("Upload assignment submission and answer key to auto-evaluate using Gemini")

tab1, tab2 = st.tabs(["Evaluate", "Dashboard"])

# Initialize result storage across runs
if "results" not in st.session_state:
    st.session_state.results = []

# ------------------ Helper Functions ------------------
def extract_text_from_file(file_path):
    if file_path.name.endswith(".docx"):
        doc = Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    elif file_path.name.endswith(".pdf"):
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        return text
    else:
        raise ValueError("Unsupported file type. Please upload a .docx or .pdf")

def extract_images_from_docx(file_obj):
    temp_path = "temp.docx"
    with open(temp_path, "wb") as f:
        f.write(file_obj.getbuffer())
    doc = Document(temp_path)
    os.makedirs("images", exist_ok=True)
    rels = doc.part._rels
    paths = []
    for i, rel in enumerate(rels.values(), 1):
        if "image" in rel.target_ref:
            image_data = rel.target_part.blob
            path = f"images/image_{i}.png"
            with open(path, "wb") as f:
                f.write(image_data)
            paths.append(path)
    return paths

def extract_text_from_images(paths):
    ocr = {}
    for p in paths:
        try:
            img = Image.open(p)
            ocr[p] = pytesseract.image_to_string(img)
        except Exception as e:
            ocr[p] = f"Error: {e}"
    return ocr

def segment_by_questions(text):
    pattern = r"(?:^|\n)(?:Q)?(\d{1,2})[).:]"
    parts = re.split(pattern, text)
    qmap = {}
    for i in range(1, len(parts), 2):
        qmap[parts[i].strip()] = parts[i+1].strip()
    return qmap

def extract_student_name(text):
    prompt = f"""
You are an intelligent assistant helping extract student details.
From the following assignment submission content, extract only the **student's full name**. If no clear name is found, respond with "Anonymous".
Text:
{text[:1500]}
Respond in format:
Name: <full name or Anonymous>
"""
    try:
        response = model.generate_content(prompt)
        lines = response.text.strip().splitlines()
        for line in lines:
            if line.lower().startswith("name:"):
                return line.split(":", 1)[1].strip()
        return "Anonymous"
    except:
        return "Anonymous"

def score_answer_with_gemini(q_num, q_text, model_ans, student_ans):
    prompt = f"""
You are an experienced university examiner at DTU, evaluating technical assignment answers.
Assess the student's answer by comparing it to the model answer provided by the professor. I want you to be strict, harsh cut marks wherever can
Evaluation Criteria:
- Conceptual correctness
- Completeness
- Relevance
- Terminology and structure
---
Question {q_num}: {q_text}
Model Answer:
{model_ans}
Student Answer:
{student_ans}
---
Return only:
Score: X/10
Feedback: One clear, academic sentence justifying the score.
"""
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error: {e}"

def detect_ai_generated_answer(student_answer, question_text):
    prompt = f"""
You are an AI text detection expert. Think wisely before you mark it AI-generated or human-written
Question: {question_text}
Answer:
{student_answer}
Respond with one of the following:
- Likely AI-generated
- Likely human-written
- Uncertain
Also provide a short justification.
Format:
Verdict: <one of the above>
Reason: <brief explanation>
"""
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error: {e}"

def adjust_score_for_ai(score_text, ai_verdict, penalty=5):
    match = re.search(r"Score:\s*(\d+(?:\.\d+)?)/10", score_text)
    if not match:
        return score_text
    score = float(match.group(1))
    is_ai = "likely ai-generated" in ai_verdict.lower()
    adjusted = max(score - penalty, 0) if is_ai else score
    result = re.sub(r"Score:\s*\d+(?:\.\d+)?/10", f"Score: {adjusted}/10", score_text)
    if adjusted != score:
        result += f"\n(Note: -{penalty} penalty applied due to AI-generated suspicion.)"
    return result

# ------------------ Evaluate Tab ------------------
with tab1:
    student_file = st.file_uploader("Upload Student Assignment (.docx or .pdf)", type=["pdf", "docx"])
    answer_key_file = st.file_uploader("Upload Answer Key (.docx or .pdf)", type=["pdf", "docx"])

    if student_file and answer_key_file:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel(model_name="models/gemini-2.5-flash")

        with st.spinner("Processing files..."):
            text = extract_text_from_file(student_file)
            ocr = ""
            if student_file.name.endswith(".docx"):
                imgs = extract_images_from_docx(student_file)
                ocr_texts = extract_text_from_images(imgs)
                ocr = "\n".join(ocr_texts.values())
            full_text = text + "\n" + ocr
            questions = segment_by_questions(full_text)
            student_name = extract_student_name(full_text)

            key_text = extract_text_from_file(answer_key_file)
            if answer_key_file.name.endswith(".docx"):
                key_imgs = extract_images_from_docx(answer_key_file)
                key_ocr = extract_text_from_images(key_imgs)
                key_text += "\n" + "\n".join(key_ocr.values())
            model_answers = segment_by_questions(key_text)

            expected = set(model_answers.keys())
            attempted = set(questions.keys())
            missing = expected - attempted

            if missing:
                st.warning("Unattempted Questions: " + ", ".join(sorted(missing)))

            student_row = {"Student": student_name}
            total = 0
            remarks = []

            for q_num, ans in questions.items():
                if not ans.strip() or len(ans.split()) < 10:
                    continue
                model_ans = model_answers.get(q_num)
                if not model_ans:
                    continue

                score_output = score_answer_with_gemini(q_num, f"Q{q_num}", model_ans, ans)
                ai_check = detect_ai_generated_answer(ans, f"Q{q_num}")
                adjusted_score = adjust_score_for_ai(score_output, ai_check)

                score_match = re.search(r"Score:\s*(\d+(?:\.\d+)?)/10", adjusted_score)
                verdict_match = re.search(r"Verdict:\s*(.*)", ai_check)

                score_val = float(score_match.group(1)) if score_match else 0
                verdict_text = verdict_match.group(1) if verdict_match else "Unknown"
                total += score_val
                remarks.append(f"Q{q_num}: {verdict_text}")

                student_row[f"Q{q_num}"] = f"{score_val} ({verdict_text})"

            student_row["Total"] = round(total, 2)
            student_row["Remarks"] = ", ".join(remarks)
            st.session_state.results.append(student_row)

            for key, val in student_row.items():
                if key.startswith("Q"):
                    st.markdown(f"---\n### {key}")
                    st.markdown(f"**Evaluation:**\n\n{val}")

# ------------------ Dashboard Tab ------------------
with tab2:
    st.subheader("Evaluated Results Dashboard")
    if st.session_state.results:
        df = pd.DataFrame(st.session_state.results).fillna("N/A")
        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="student_evaluations.csv",
            mime="text/csv"
        )
    else:
        st.info("No evaluations yet. Submit an assignment to begin.")
