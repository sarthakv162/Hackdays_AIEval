# AIEval – DTU Assignment Evaluator

AIEval is a smart AI-based assignment evaluation system designed to automate and enhance the assessment process at Delhi Technological University (DTU) and similar academic institutions. It accepts both typed and handwritten student submissions, compares them against a professor's answer key, evaluates quality using generative AI models, and detects AI-generated content or plagiarism patterns.


## Features

- Automatic grading using large language models (Gemini)
- Semantic comparison of student answers to the answer key
- AI-generated answer detection with penalty logic
- OCR support for handwritten answers (via image extraction)
- Flexible support for PDF and DOCX input formats
- Question segmentation (handles shuffled question order)
- Per-question scoring, feedback, and AI verdict
- Downloadable evaluation results in CSV format
- Streamlit-based interactive web interface

## How It Works

1. **File Upload**
   - Professor uploads an answer key (PDF or DOCX)
   - Student uploads their assignment (PDF or DOCX)

2. **Text Extraction**
   - Typed content is extracted via `pdfplumber` or `python-docx`
   - Images inside DOCX are parsed and passed through OCR (`pytesseract`)

3. **Question Parsing**
   - Questions are segmented by regex to handle varied formats (e.g., Q1, 1., 2))

4. **Evaluation**
   - Each student answer is semantically compared to the model answer using Gemini 2.5 Flash
   - Partial scoring is applied based on relevance, completeness, and structure

5. **AI Detection**
   - Each answer is analyzed to determine if it was AI-generated
   - If flagged, a configurable penalty is applied

6. **Dashboard**
   - Results (Name, Question, Score, AI Verdict) are tabulated and available for CSV export

## Tech Stack

| Component          | Tool / Library                |
|--------------------|-------------------------------|
| UI Framework       | Streamlit                     |
| LLM API            | Google Gemini 2.5 Flash       |
| OCR Engine         | pytesseract                   |
| File Parsing       | pdfplumber, python-docx       |
| Image Handling     | Pillow (PIL)                  |
| Text Matching      | Regex, semantic prompts       |
| Data Handling      | Pandas                        |


## File Structure

```

.
├── app.py              # Main Streamlit app
├── styles.css          # Custom UI styling
├── requirements.txt    # Python dependencies
├── .devcontainer/      # Dev container setup for VS Code (optional)

````

## Installation

1. Clone the repository:

```bash
git clone https://github.com/sarthakv162/Hackdays_AIEval.git
cd Hackdays_AIEval
````

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set up your Gemini API key in `st.secrets["GEMINI_API_KEY"]`.

4. Run the app:

```bash
streamlit run app.py
```

---

## Usage Notes

* The system supports both typed and handwritten assignment PDFs or DOCX files.
* If student answers are out of order, the app re-aligns them by question number.
* Answer key and student responses should follow a standard format (e.g., `1.`, `2.` etc.) for best results.

---

## Future Improvements

* Full integration with Google Classroom API
* Support for mathematical formula recognition (via Mathpix)
* Instructor-customizable rubrics per question
* Web-hosted backend with user authentication
* Enhanced paraphrasing-based plagiarism detection
