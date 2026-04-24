from openai import OpenAI

client = OpenAI(
    base_url='https://api-inference.modelscope.cn/v1',
    api_key='ms-838f2742-51b4-4b4a-aa18-2ca0dc40caf9', # ModelScope Token
)

response = client.chat.completions.create(
    model='Qwen/Qwen3.5-397B-A17B', # ModelScope Model-Id, required
    messages=[{
        'role':
            'user',
        'content': [{
            'type': 'text',
            'text': '描述这幅图',
        }, {
            'type': 'image_url',
            'image_url': {
                'url':
                    'https://modelscope.oss-cn-beijing.aliyuncs.com/demo/images/audrey_hepburn.jpg',
            },
        }],
    }],
    stream=True
)

for chunk in response:
    if chunk.choices:
        print(chunk.choices[0].delta.content, end='', flush=True)