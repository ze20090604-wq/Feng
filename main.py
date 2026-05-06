import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage

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

    # 建立記憶體串列
    messages = []

    print("--- 進入對話模式 (具備短期記憶，輸入 '結束' 退出) ---")
    while True:
        user_input = input("你: ").strip()

        # 結束指令判斷
        if user_input.lower() in ["exit", "quit", "結束", "bye"]:
            print("AI: 再見！期待下次與你對話。")
            break

      # 空白輸入判斷
        if not user_input:
            continue

        # 1. 將本輪字句建成 HumanMessage
        human_message = HumanMessage(content=user_input)

        # 2. 組合歷史訊息與目前訊息，送給 LLM 參考
        context_messages = [*messages, human_message]

        try:
            print("AI: ", end="", flush=True)
            full_response_content = "" # 用來累積串流內容
            
            # 3. 將 context_messages 送給 LLM
            for chunk in llm.stream(context_messages):
                if chunk.content:
                    print(chunk.content, end="", flush=True)
                    full_response_content += chunk.content # 累積回應內容
            
            print("\n")

            # 4. 串流結束後，將 HumanMessage 及 AIMessage 存進 messages
            ai_message = AIMessage(content=full_response_content)
            messages.append(human_message)
            messages.append(ai_message)
            
        except Exception as e:
            print(f"發生錯誤: {e}")

if __name__ == "__main__":
    main()
