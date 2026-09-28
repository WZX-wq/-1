import json

import requests
import whisper
import os
import zhconv
from openai import OpenAI


model_type = input('请选择语音识别模型类型 tiny、base、small、medium、large:\n')
print(f'正在加载语音识别模型openai-whisper---{model_type}，首次打开需要下载')
# 加载模型（首次运行会自动下载模型）
model = whisper.load_model(model_type)  # 中文建议用 medium 或 large


def transcribe_folder(folder_path, method_num):
    code = ''
    online_url = ''
    if method_num == '1':
        code = input('请输入api的code(秘钥)：\n')
    if method_num == '2':
        online_url = input('请输入自部署的api地址：\n')
    # 确保文件夹存在
    if not os.path.exists(folder_path):
        print(f"文件夹 {folder_path} 不存在")
        return

    # 遍历文件夹中的所有文件
    for filename in os.listdir(folder_path):
        # 构造文件的完整路径
        file_path = os.path.join(folder_path, filename)

        # 检查是否是视频文件
        if os.path.isfile(file_path):
            # 获取文件名（不含扩展名）
            base_filename = os.path.splitext(filename)[0]
            output_file = os.path.join(folder_path, f"{base_filename}.txt")

            # 如果已经存在对应的文本文件，跳过处理
            if os.path.exists(output_file):
                print(f"跳过已处理的文件：{filename}")
                continue

            # 转写视频文件
            try:
                # 使用 initial_prompt 参数，确保输出简体中文
                result = model.transcribe(file_path, language="zh", initial_prompt="以下是普通话的句子。")

                # 如果仍然输出繁体字，使用 zhconv 转换为简体
                result["text"] = zhconv.convert(result["text"], "zh-cn")

                print(f"\n提取 {filename} 的文字内容：\n", result["text"])

                if method_num == '0':
                    result["text"] = result["text"]
                if method_num == '1':
                    result["text"] = deepseek_ai(code, base_filename, result["text"])
                if method_num == '2':
                    result["text"] = self_deepseek_ai(online_url, base_filename, result["text"])
                    if result["text"] != 'AI处理失败':
                        result["text"] = result["text"].split('</think>')[1]

                print(f"\n最终 {filename}的文字内容：\n", result["text"])

                # 保存结果到与视频文件同名的文本文件
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(result["text"])
                print(f"结果已保存到 {output_file}")
            except Exception as e:
                print(f"处理文件 {filename} 时出错：{e}")
        else:
            print(f"跳过非文件项 {filename}")


def deepseek_ai(code, title, text):
    #"sk-662e05907f704994a4d7a53d0d097cc7"
    client = OpenAI(api_key=code, base_url="https://api.deepseek.com")

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "你是一个文本修正助手。"},
            {"role": "user",
             "content": f'{text} 请你帮忙修改这段话的错误，这是一段通过语音识别获取的文字，需要修改其中的谐音词，这是这段话的标题：{title}，内容修改完后必须符合标题，修改完直接返回结果就行'},
        ],
        stream=False
    )

    return response.choices[0].message.content


def self_deepseek_ai(online_url, title, text):
    # 定义 API 地址和请求数据
    url = online_url +"/api/chat"
    payload = {
        "model": "deepseek-r1:7b",
        "messages": [
            {"role": "system", "content": "你是一个文本修正助手。"},
            {"role": "user",
             "content":  f"{text}  这是一段通过语音识别获取的文字，这段话的标题：{title}，有些语音识别文字不准确，请修改不准确的部分，内容必须符合标题，逻辑通顺，完成后只返回修改后的内容"},
        ],
        "stream": False,
        "temperature": 0.3
    }

    # 设置请求头
    headers = {
        "Content-Type": "application/json"
    }

    # 发送 POST 请求
    response = requests.post(url, json=payload, headers=headers, verify=False)

    if response.status_code == 200:
        message = json.loads(response.text)
        return message['message']['content']
    else:
        return 'AI处理失败'


# 指定文件夹路径
folder_path = input('请输入视频文件夹路径：\n ')
# 指定处理方法
method_num = input('请选择处理方法：0.不使用ai处理 1.调用api(付费) 2.自部署 \n ')
# 执行转写
transcribe_folder(folder_path, method_num)

