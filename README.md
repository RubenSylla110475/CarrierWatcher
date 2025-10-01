# 📊 CarrierWatcher

**CarrierWatcher** is a Streamlit application that helps you **manually track your internship applications**. All applications are stored in a local Excel file (`data/applications.xlsx`), and the interface provides a clear and professional view of your progress.

---

## 🚀 Features

- Simple form to add an application (code, company, topic, domain, dates, status).
- Dashboard summarizing the total number of applications, accepted, rejected, and pending ones.
- Filterable table by status, domain, and topic.
- Chart showing the distribution of applications by status.
- Local Excel storage to keep all applications organized.
- Synchronization button to automatically import application emails from Outlook (Microsoft 365).

---

## 🧰 Requirements

- Python 3.9 or higher

---

## 📦 Installation

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## ▶️ Running the Application

```bash
streamlit run app.py
```

The first time you run the application, it will automatically create the `data` folder and the Excel tracking file.  
You can then access the application in your browser at the URL provided by Streamlit (usually `http://localhost:8501`).

---

## 📬 Synchronizing Your Outlook Mailbox

The application can automatically import your internship applications from the mailbox `ruben.sylla@edu.ece.fr` (or any other Microsoft 365 account) using the Microsoft Graph API. There are two synchronization options:

1. **From the Streamlit interface:** Click on **“Synchronize mailbox now”** to launch a one-time synchronization. A summary of scanned emails, created applications, and updates will then be displayed.  
2. **From a standalone script:** Run `python mail_sync.py` to synchronize without starting Streamlit (useful for manual or scheduled runs).

---

### 🛠️ First-Time Setup

Before the first synchronization:

1. Create a Microsoft Entra ID (Azure AD) application from [portal.azure.com](https://portal.azure.com).  
   - Account type: “Accounts in any organizational directory”.  
   - Save the **Application (client) ID**.
2. In **API permissions**, add the delegated permissions **Mail.Read** and **offline_access** for Microsoft Graph, then grant admin consent if required.
3. Set the `AZURE_CLIENT_ID` environment variable with the retrieved client ID.

When you run the script for the first time (via the Streamlit button or with `python mail_sync.py`), Microsoft will display a URL and a code to authorize mailbox access.  
Access tokens are cached in `data/token_cache.json` so you don’t have to log in again for future synchronizations.

---

### 📧 Email Import Behavior

Detected emails are matched with existing applications based on the **company name**. When a new email is imported, the application will:

- Create a new row if no matching application exists.  
- Update the status based on keywords (*Pending*, *Interview*, *Accepted*, *Rejected*).  
- Save the date of the last email and mark **"email"** in the **Source** column.

You can also automate synchronization using **Windows Task Scheduler** by regularly running:

```bash
python mail_sync.py
```

---

## 📊 Excel File Structure

Each row in `data/applications.xlsx` contains the following information:

- Application code  
- Company  
- Topic  
- Domain  
- Status  
- Application date  
- Internship start date  
- Last email (timestamp of the last synchronized email)  
- Source ("email" when the application is created from synchronization)

These columns can also be manually edited in Excel if necessary — the application will keep them intact on future reads.
