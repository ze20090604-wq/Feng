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

    llm = ChatOpenAI(
        model=model,
        temperature=0.6,
        base_url=base_url,
        api_key=api_key
    )

    print("--- 進入對話模式 (輸入 '結束'、'exit' 或 'quit' 退出) ---")
    while True:
        user_input = input("你: ").strip()

        if user_input.lower() in ["exit", "quit", "結束", "bye"]:
            print("AI: 再見！期待下次與你對話。")
            break

        if not user_input:
            continue

        try:
            print("AI: ", end="", flush=True)
            for chunk in llm.stream(user_input):
                if chunk.content:
                    print(chunk.content, end="", flush=True)
            print("\n")
        except Exception as e:
            print(f"發生錯誤: {e}")

if __name__ == "__main__":
    main()
