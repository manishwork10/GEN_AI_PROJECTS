import os
from langchain_community.vectorstores import FAISS
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.document_loaders import UnstructuredPDFLoader



# Sir lai sodne

# Google API key
# from dotenv import load_dotenv
# load_dotenv()

# api_key=os.environ["Goggle_Api_Key"]

# os.environ["GOOGLE_API_KEY"] = "AIzaSyBNF72RkqAhpERKmMHpY75a_cOqOZGKMTw"
import os
API_TOKEN = os.getenv("Goggle_Api_Key")

# ----------------------------
# Load PDF and Create Vector Store
# ---------------------------- for the loading one pdf
# try:
#     loader = PyPDFLoader("mypdf.pdf")
#     documents = loader.load()
# except Exception as e:
#     print(f"Error loading PDF. Make sure 'mypdf.pdf' is in the directory.")
#     print(f"Error: {e}")
#     # Create a dummy document to allow the script to run for demonstration
#     from langchain_core.documents import Document
#     documents = [Document(page_content="This is a dummy document. Replace mypdf.pdf with your own file to get real answers.")]

# try:
pdf_paths = ["Computer_Network.pdf", "Insights_on_Computer_Networks_1680315871004.pdf"]  # List your PDF files here
#     documents = []
#     for path in pdf_paths:
#         loader = UnstructuredPDFLoader(path)
#         loaded_docs = loader.load()
#         for doc in loaded_docs:
#             doc.metadata["source"] = path
#         documents.extend(loaded_docs)
# except Exception as e:
#     print(f"Error loading PDFs. Make sure the files exist in the directory.")
#     print(f"Error: {e}")
#     from langchain_core.documents import Document
#     documents = [Document(page_content="This is a dummy document. Replace PDFs with your own files to get real answers.")]

# 2nd try
documents = []

for path in pdf_paths:
    try:
        print(f"🔍 Loading: {path}")
        loader = UnstructuredPDFLoader(path)
        loaded_docs = loader.load()
        print(f"✅ Loaded {len(loaded_docs)} pages from {path}")
        for doc in loaded_docs:
            doc.metadata["source"] = path
        documents.extend(loaded_docs)
    except Exception as e:
        print(f"❌ Failed to load {path}: {e}")

splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
docs = splitter.split_documents(documents)

embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
vector_store = FAISS.from_documents(docs, embedding=embeddings)
retriever = vector_store.as_retriever(search_kwargs={"k": 5})

# ----------------------------
# Build LLM and Chains using modern LCEL
# ----------------------------
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3, max_tokens=500)

# Contextualize Question Prompt: This prompt takes the chat history and a new question,
contextualize_q_system_prompt = (
    "Given a chat history and the latest user question "
    "Always consider and remember the previous conversation history to maintain context, track facts (like the user's name), "
    "and provide accurate, coherent responses across multiple turns.\n\n"
    "without the chat history. Do NOT answer the question, "
    "just reformulate it if needed and otherwise return it as is."
)

contextualize_q_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", contextualize_q_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
)

# Chain to rephrase the question
history_aware_retriever = create_history_aware_retriever(
    llm, retriever, contextualize_q_prompt
)

# Answering Prompt: 
qa_system_prompt = (
    "You are an intelligent and helpful AI assistant engaged in an ongoing conversation with a human user. "
    "Use the retrieved context from documents as well as the chat history to answer the current question or input. "
    "If the answer is not found in the context or memory, say that you don't know. "
    "Keep your responses concise and to the point — limit answers to a maximum of three sentences.\n\n"

    "Respond as the assistant (you), and treat the input as coming from the user (the other person in the chat).\n\n"
    "{context}"
)

qa_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", qa_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
)

# Chain to combine documents and generate an answer
qa_chain = create_stuff_documents_chain(llm, qa_prompt)

# The final RAG chain that combines the history-aware retriever and the answering chain
rag_chain = create_retrieval_chain(history_aware_retriever, qa_chain)


# This wrapper makes the chain stateful by managing chat history per session_id.
store = {}

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    """Gets the chat history for a given session ID."""
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

conversational_rag_chain = RunnableWithMessageHistory(
    rag_chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history",
    output_messages_key="answer",
)

# ----------------------------
# Chat Section
# ----------------------------
print("\n--- Conversational RAG Ready ---")
print("Type your question or message. Type 'exit' to quit.\n")

session_id = "my_chat_session_123"

while True:
    user_input = input("You: ")
    if user_input.lower() in ["exit", "quit"]:
        print("Goodbye!")
        break

    result = conversational_rag_chain.invoke(
        {"input": user_input},
        config={"configurable": {"session_id": session_id}}
    )

    # print("\n\n--- RETRIEVED CONTEXT ---\n")
    # if result.get("context"):
    #     for i, doc in enumerate(result["context"]):
    #         print(f"Chunk {i+1}:\n{doc.page_content}\n")
    # else:
    #     print("No context was retrieved.")
    # print("--------------------------\n\n")
    # #----------------------------------------
    print("\n\n--- RETRIEVED CONTEXT ---\n")
    if result.get("context"):
        for i, doc in enumerate(result["context"]):
            print(f"Chunk {i+1} from: {doc.metadata.get('source', 'Unknown')}\n")
            print(doc.page_content[:500])  # Only printing first 500 chars for brevity
            print("-" * 50)
    else:
        print("No context was retrieved.")
    print("--------------------------\n\n")


    answer = result.get("answer", "Sorry, I could not process that.")
    print(f"AI: {answer}")