from openai import OpenAI
import time

class GPT4o:
    api_base = ""
    api_key= ""
    deployment_name = 'gpt-4o'
    completion_tokens = 0
    prompt_tokens = 0
    def __init__(self):
        self.client = OpenAI(
            api_key=self.api_key,  
            base_url=self.api_base
        )
    def send_single_request(self, messages, temperature=0.0):
        result = self.client.chat.completions.create(
            model=self.deployment_name,
            messages=messages,
            temperature=temperature,
        )
        print(f"token=({result.usage.completion_tokens}, {result.usage.prompt_tokens})")
        self.completion_tokens += result.usage.completion_tokens
        self.prompt_tokens += result.usage.prompt_tokens
        return result

    def send_stable_request(self, messages, retry=10, temperature=0.0):
        print("GPT API CALL")
        for i in range(retry):
            try:
                result = self.send_single_request(messages, temperature=temperature)
                print(f"try {i}: total_token=({self.completion_tokens}, {self.prompt_tokens})")
                if not result.choices[0].message.content:
                    print(f"[Error] empty response: {result}")
                    continue
                return result.choices[0].message.content
            except Exception as e:
                print(f"[Error] API Return Error: {e}")
                time.sleep(1)
                continue
        raise(Exception("Retry time limit exceeded"))