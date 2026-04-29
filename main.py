import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

def main():
    load_dotenv()
    api_key = os.getenv("OPEN_API_KEY")
    
    if api_key:
        print(f"open_API_KEY: 已設定")
    else:
        print("open_API_KEY 未設定") 
        return 
    base_url = os.getenv("BASE_URL")
    model = os.getenv("MODEL")
    # agant_name = "AI_hong"
    # print(f"Hello, 我是 {agant_name}")

    llm = ChatOpenAI(
        model=model,
        temperature=0.6,
        base_url=base_url,
        api_key=api_key
    )

    user_message = "你好，可以回答我問題嗎？"
    response = llm.invoke(user_message)

    print(f"AI 回應內容:\n{response.content}")

if __name__ == "__main__":
    main()
