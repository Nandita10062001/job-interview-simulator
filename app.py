import streamlit as st
import json
import openai
import time

def call_openai(prompt: str, model="gpt-4o"):
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
st.subheader("Job Description → Interview Questions")
st.markdown("This demo shows the various functionalities of SwitchCareers.")

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
            You are a professional recruiter. 

            Create a detailed, professional, and engaging **job description** for a **{job_role}** role at **{company_name}**.

            ### Guidelines:
            - The job description must be tailored specifically to **{job_role}** at **{company_name}**.
            - Use an engaging tone like seen in job postings on platforms like LinkedIn or Indeed.
            - Include clear sections:
                - **Job Title**
                - **Job Type & Work Arrangement** (e.g. Remote/Hybrid/Onsite, Full-time/Part-time)
                - **Salary Range**
                - **Location**
                - **Requirements** (as 2-3 bullet points)
                - **Responsibilities** (as 2-3 bullet points)
            - Mention relevant technologies, tools, or domain practices.
            - Use job market insights to propose salary range and location.
            - **[IMPORTANT] Present the output in clear formatted text with headings, bold, and bullet points. Do NOT use JSON format. Do NOT use code blocks.**
            """

        content = call_openai(prompt)
        if content:
            try:
                st.session_state.job_description = json.loads(content)
            except json.JSONDecodeError:
                st.session_state.job_description = content

        st.success("Job description generated!")
    
    # Step 2: Resume
    with st.spinner("Generating Resume..."):
        job_desc_str = json.dumps(st.session_state.job_description, indent=2) \
            if isinstance(st.session_state.job_description, dict) else st.session_state.job_description

        name_prompt = """
        Generate only ONE random, realistic Indian full name (first name and last name).
        The response should contain only the name, nothing else.
        """
        candidate_name = call_openai(name_prompt) or "Nandita Nandakumar"  # Fallback if API fails

        prompt = f"""
        You are an expert resume writer.

        Generate a realistic, professional resume tailored to the following job description for a candidate named **{candidate_name}**.

        Include realistic company names, job titles, universities, and certifications relevant to the role.

        Use current best practices in resume writing and avoid generic placeholders like "XYZ" or "ABC". The resume should include:

        - Contact Information (use realistic but fake values)
        - Summary
        - Work Experience
        - Education (realistic universities and degrees)
        - Skills
        - Certifications

        Job Description:
        {job_desc_str}
        """

        st.session_state.resume_content = call_openai(prompt)

# Display Job Description
if st.session_state.job_description:
    st.subheader("Job Description:")
    if isinstance(st.session_state.job_description, dict):
        st.markdown(st.session_state.job_description)
    else:
        st.text_area("Job Description", st.session_state.job_description, height=300)

# Display Resume
if st.session_state.resume_content:
    st.subheader("Candidate Resume:")
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
            user_response = st.text_area("Your response:", height=100, key=text_area_key)
            
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
1. Enter your OpenAI API key to activate the AI recruiter workflow.
2. Input **Company Name** and **Job Role** to auto-generate a tailored Job Description for recruiters to post.
3. Instantly see the AI-generated **Top Candidate's Resume** for the role.
4. Preview the **AI-driven Candidate Interview Flow & Questions** to experience how the system works.
""")
