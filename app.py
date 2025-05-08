import streamlit as st
import json
import openai
import time

# ------------------- Helper Function -------------------

def call_openai(prompt: str, model="gpt-3.5-turbo"):
    try:
        response = openai.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"OpenAI API call failed: {str(e)}")
        return None

def remove_placeholders(text):
    """Remove common placeholders like [Your Name] from text"""
    import re
    pattern = r'\[(.*?)\]|<(.*?)>'
    return re.sub(pattern, "Interviewer", text)

# ------------------- Session State ---------------------

defaults = {
    'job_title': "",
    'job_description': None,
    'resume_content': None,
    'company': "",
    'count': 0,
    'interview_history': [],
    'interview_started': False,
    'interview_completed': False,
    'user_input': "",
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ------------------- UI ---------------------

st.title("Demo")
st.subheader("Job Description → Resume → Interview Questions")
st.markdown("This demo shows how outputs from one AI prompt become inputs for subsequent prompts.")

api_key = st.sidebar.text_input("Enter your OpenAI API Key:", type="password")
if api_key:
    openai.api_key = api_key

# Step 1: Job Description Generation
st.header("Step 1: Generate Job Description")

company_name = st.text_input("Enter the company name:", value=st.session_state.company)
job_role = st.text_input("Enter a job role (e.g., 'Senior Data Scientist'):", 
                         value=st.session_state.job_title)

if st.button("Generate Job Description") and job_role and api_key:
    with st.spinner("Generating job description..."):
        st.session_state.job_title = job_role
        st.session_state.company = company_name

        prompt = f"""
        Create a detailed job description for a **{job_role}** role at **{company_name}**, in structured JSON format.

        ### Guidelines:
        - The job description must be tailored specifically to **{job_role}** at **{company_name}**.
        - Include industry-relevant **requirements** and **responsibilities**.
        - Mention technologies or tools this company might use.
        - Use job market insights to define salary and job type.
        - [STRICTLY] Structure the response exactly as follows:
        {{
            "title": "{job_role}",
            "type": "<Specify Remote/Hybrid/Onsite, Full-time/Part-time based on the role>",
            "salary_range": "<Generate a realistic salary range>",
            "requirements": [
                "<Years of experience required>",
                "<Key skills and domain expertise>",
                "<Commonly required certifications (if any)>",
                "<Additional 2-3 role-specific qualifications>"
            ],
            "responsibilities": [
                "<Core daily tasks>",
                "<Collaboration aspects>",
                "<Technical or managerial expectations>",
                "<2-3 additional responsibilities for this role>"
            ],
            "location": "<Generate a realistic location>"
        }}
        """
        content = call_openai(prompt)
        if content:
            try:
                st.session_state.job_description = json.loads(content)
            except json.JSONDecodeError:
                st.session_state.job_description = content

        st.success("Job description generated!")

# Display Job Description
if st.session_state.job_description:
    st.subheader("Generated Job Description:")
    if isinstance(st.session_state.job_description, dict):
        st.json(st.session_state.job_description)
    else:
        st.text_area("Job Description", st.session_state.job_description, height=300)

# Step 2: Resume Generation
if st.session_state.job_description:
    st.header("Step 2: Generate Resume")

    user_name = st.text_input("Enter your full name for the resume:")
    
    if st.button("Generate Tailored Resume") and user_name:
        with st.spinner("Generating resume..."):
            job_desc_str = json.dumps(st.session_state.job_description, indent=2) \
                if isinstance(st.session_state.job_description, dict) else st.session_state.job_description

            prompt = f"""
            You are an expert resume writer.

            Generate a realistic, professional resume tailored to the following job description for a candidate named **{user_name}**.

            Include realistic company names, job titles, universities, and certifications relevant to the role.

            Use current best practices in resume writing and avoid generic placeholders like "XYZ" or "ABC". The resume should include:

            - Contact Information (use realistic but fake values)
            - Summary
            - Work Experience (include realistic company names, locations, dates, responsibilities)
            - Education (realistic universities and degrees)
            - Skills
            - Certifications

            Job Description:
            {job_desc_str}
            """

            st.session_state.resume_content = call_openai(prompt)

        st.success("Resume generated!")

    if st.session_state.resume_content:
        st.subheader("Generated Resume:")
        st.markdown(st.session_state.resume_content)

# Step 3: Interview
if st.session_state.job_description and st.session_state.resume_content:
    st.header("Step 3: Start Interview")

    if not st.session_state.interview_started and st.button("Start Interview"):
        with st.spinner("Starting interview..."):
            job_desc_str = json.dumps(st.session_state.job_description, indent=2) \
                if isinstance(st.session_state.job_description, dict) else st.session_state.job_description

            prompt = f"""
            You are a recruiter for {st.session_state.company} hiring a {st.session_state.job_title}.
            
            IMPORTANT: Do NOT use any placeholders like [Your Name] or [Company Name]. 
            
            Greet the candidate and ask about a specific relevant experience from their resume.

            Candidate Resume:
            {st.session_state.resume_content}

            Job Description:
            {job_desc_str}
            """
            first_question = call_openai(prompt)
            if first_question:
                first_question = remove_placeholders(first_question)
                st.session_state.interview_started = True
                st.session_state.count = 1
                st.session_state.interview_history.append(("interviewer", first_question))

    if st.session_state.interview_started:
        st.subheader("Interview Session:")
        for role, text in st.session_state.interview_history:
            if role == "interviewer":
                st.markdown(f"🎙️ **Interviewer**: {text}")
            else:
                st.markdown(f"👤 **You**: {text}")

        if not st.session_state.interview_completed:
            text_area_key = f"response_input_{st.session_state.count}"
            user_response = st.text_area("Your response:", height=100,key=text_area_key)
            
            if st.button("Submit Response"):
                if user_response:
                    st.session_state.interview_history.append(("candidate", user_response))
                    
                    if st.session_state.count >= 5:
                        prompt = f"""
                        The interview for {st.session_state.job_title} has concluded.
                        Write a short thank-you message to the candidate.
                        
                        IMPORTANT: Do NOT use any placeholders like [Your Name] or [Company Name].
                        """
                        closing = call_openai(prompt)
                        if closing:
                            closing = remove_placeholders(closing)
                            st.session_state.interview_history.append(("interviewer", closing))
                        st.session_state.interview_completed = True
                        st.rerun()
                    else:
                        with st.spinner("Interviewer is typing..."):
                            job_desc_str = json.dumps(st.session_state.job_description, indent=2) \
                                if isinstance(st.session_state.job_description, dict) else st.session_state.job_description

                            conversation = "\n".join(
                                [f"{'Interviewer' if r == 'interviewer' else 'Candidate'}: {t}" for r, t in st.session_state.interview_history]
                            )

                            prompt = f"""
                            Continue the interview for {st.session_state.job_title} at {st.session_state.company}.

                            Based on the following conversation, generate ONLY ONE follow-up question.
                            
                            IMPORTANT: 
                            1. Do NOT use any placeholders like [Your Name] or [Company Name].
                            2. Do NOT prefix your response with "Interviewer:" - just ask your question directly.
                            3. Use the actual company name ({st.session_state.company}).

                            Interview so far:
                            {conversation}

                            Job Description:
                            {job_desc_str}
                            """

                            next_q = call_openai(prompt)
                            if next_q:
                                next_q = remove_placeholders(next_q)
                                st.session_state.count += 1
                                st.session_state.interview_history.append(("interviewer", next_q))

                        st.rerun()

# Reset Button
if st.session_state.job_description or st.session_state.resume_content or st.session_state.interview_started:
    if st.sidebar.button("Reset Demo"):
        for key in defaults:
            st.session_state[key] = defaults[key]
        st.rerun()

# Sidebar Instructions
st.sidebar.markdown("## How to Use")
st.sidebar.markdown("""
1. Enter your OpenAI API key  
2. Enter the **company name** and **job role**  
3. Generate a tailored job description  
4. Generate a tailored resume  
5. Start and complete a 5-question interview  
""")