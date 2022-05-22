from asyncio import tasks
import asyncio
import websockets
import re
import shortuuid
import asyncio
from websockets import connection, client
import websockets
from datetime import datetime
import logging
import json
from websockets.extensions.permessage_deflate import (
    ServerPerMessageDeflateFactory,
    ClientPerMessageDeflateFactory,
)
from websocket import create_connection
from uuid import uuid1, uuid4
from requests import Session
import simpleaudio as sa
import sounddevice as sd
import soundfile as sf
from playsound import playsound

#   TTS文字转语音
class TTS:
    def __init__(self):
        self.request = Session()
        self.headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.41 Safari/537.36",
            "referer": "https://azure.microsoft.com",
            "origin": "https://azure.microsoft.com/",
            "authorization": "",
        }
        self.wss_url = (
            "wss://eastus.tts.speech.microsoft.com/cognitiveservices/websocket/v1"
        )

        self.auth = "Authorization"
        self.token = ""
        #   参数列表
        self.params_list = []
        self.ws = None
        #   音频数据列表
        self.audio_map = {}
        #   当前请求id
        self.now_request = ""

        self.get_token()

        #   websocket日志
        logger = logging.getLogger("websockets")
        # logger = logging.getLogger("websockets.client")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(logging.StreamHandler())

        #   平台信息
        self.platform = {
            "context": {
                "system": {
                    "name": "SpeechSDK",
                    "version": "1.19.0",
                    "build": "JavaScript",
                    "lang": "JavaScript",
                },
                "os": {
                    "platform": "Browser/Win32",
                    "name": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.41 Safari/537.36",
                    "version": "5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.41 Safari/537.36",
                },
            }
        }
        #   语音信息
        self.voice = {
            "synthesis": {
                "audio": {
                    "metadataOptions": {
                        "bookmarkEnabled": False,
                        "sentenceBoundaryEnabled": False,
                        "visemeEnabled": False,
                        "wordBoundaryEnabled": False,
                    },
                    "outputFormat": "audio-24khz-160kbitrate-mono-mp3",
                },
                "language": {"autoDetection": False},
            }
        }

    @property
    def authorization(self):
        return f"Bearer {self.token}"

    #   连接id
    @property
    def connection_id(self):
        return shortuuid.ShortUUID().random(32)

    #   请求id
    @property
    def requestId(self):
        # return shortuuid.ShortUUID().random(32).upper()
        return str(uuid1()).replace("-", "").upper()
        # return "EC7237308086480693BFEE6A20044BF3"

    @property
    def ws_url(self):
        return f"{self.wss_url}?Authorization=bearer%20{self.token}&X-ConnectionId={self.connection_id}"

    #   当前时间字符串
    @property
    def now_time(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        return now[:-3] + "Z"

    #   获取首页token
    def get_token(self):
        """
        url:https://azure.microsoft.com/zh-cn/services/cognitive-services/text-to-speech/
        """
        logging.debug("获取token")
        result = self.request.get(
            "https://azure.microsoft.com/zh-cn/services/cognitive-services/text-to-speech/",
            headers={
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.41 Safari/537.36"
            },
            proxies={"http": "", "https": ""},
            verify=False,
        )
        if result.status_code != 200:
            print("请求token失败", result.status_code)
            return
        data = result.text
        reg = re.compile(r'token: "(.*?)"')
        token_list = reg.findall(data)
        if len(token_list) <= 0:
            print("未获取到token")
            return
        self.token = token_list[0]
        self.headers["authorization"] = self.authorization
        print(self.token)

    #   获取数据
    def get_data(
        self,
    ):
        """
        链接url：https://eastus.tts.speech.microsoft.com/cognitiveservices/voices/list
        """
        logging.debug("获取数据")
        result = self.request.get(
            "https://eastus.tts.speech.microsoft.com/cognitiveservices/voices/list",
            headers=self.headers,
            proxies={"http": "", "https": ""},
            verify=False,
        )

        if result.status_code != 200:
            print("请求失败", result.status_code)
            return
        data = result.json()
        self.params_list = data

    #   连接WebSocket
    def connect_ws(self, sync=False):
        self.get_data()
        # ws = await websockets.connect(
        #     self.ws_url,
        #     origin="https://azure.microsoft.com",
        #     extra_headers={
        #         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.41 Safari/537.36",
        #         "Host": "eastus.tts.speech.microsoft.com",
        #     },
        #     extensions=[ClientPerMessageDeflateFactory(client_max_window_bits=True)],
        # )
        print(self.ws_url)
        ws = create_connection(self.ws_url)
        self.ws = ws
        return self.ws

    #   异步连接WS
    async def async_connect_ws(self):
        self.get_data()
        print(self.ws_url)
        cookie_dict = self.request.cookies.get_dict()
        cookie_list = []
        for key in cookie_dict:
            cookie_list.append(f"{key}={cookie_dict[key]}")
        ws = await websockets.connect(
            self.ws_url,
            # origin="https://azure.microsoft.com",
            extra_headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.41 Safari/537.36",
                # "Host": "eastus.tts.speech.microsoft.com",
                # "Cookie": ";".join(cookie_list),
            },
            extensions=[ClientPerMessageDeflateFactory(client_max_window_bits=True)],
        )
        self.ws = ws
        return self.ws

        # async with websockets.connect(
        #     self.ws_url,
        #     #   不需要额外的请求头
        #     # extra_headers={
        #     #     "Host": "eastus.tts.speech.microsoft.com",
        #     #     "Origin": "https://azure.microsoft.com",
        #     #     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.41 Safari/537.36",
        #     #     "Sec-WebSocket-Extensions": "permessage-deflate; client_max_window_bits",
        #     #     "Sec-WebSocket-Key": "7mupLdK2iBPG7DudstgUPA==",
        #     #     "Sec-WebSocket-Version": "13",
        #     # },
        # ) as ws:
        #     self.ws = ws
        # while True:
        #     data = await ws.recv()
        #     print(data)

    #         #   发送数据之前
    #         def before_send(self):
    #             if not self.flag:
    #                 #   第一步
    #                 self.ws.send(
    #                     """Path: speech.config
    # X-RequestId: B237EEEEDBE7442DB3889EDB6C76A245
    # X-Timestamp: 2022-05-21T03:50:01.359Z
    # Content-Type: application/json

    # {"context":{"system":{"name":"SpeechSDK","version":"1.19.0","build":"JavaScript","lang":"JavaScript"},"os":{"platform":"Browser/Win32","name":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.41 Safari/537.36","version":"5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.41 Safari/537.36"}}}"""
    #                 )
    #                 #   第二步
    #                 self.ws.send(
    #                     """Path: synthesis.context
    # X-RequestId: B237EEEEDBE7442DB3889EDB6C76A245
    # X-Timestamp: 2022-05-21T03:50:01.360Z
    # Content-Type: application/json

    # {"synthesis":{"audio":{"metadataOptions":{"bookmarkEnabled":false,"sentenceBoundaryEnabled":false,"visemeEnabled":false,"wordBoundaryEnabled":false},"outputFormat":"audio-24khz-160kbitrate-mono-mp3"},"language":{"autoDetection":false}}}"""
    #                 )
    #                 self.ws.send(
    #                     """Path: ssml
    # X-RequestId: B237EEEEDBE7442DB3889EDB6C76A245
    # X-Timestamp: 2022-05-21T03:50:01.360Z
    # Content-Type: application/ssml+xml

    # <speak xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="http://www.w3.org/2001/mstts" xmlns:emo="http://www.w3.org/2009/10/emotionml" version="1.0" xml:lang="en-US"><voice name="zh-CN-XiaoxiaoNeural"><prosody rate="0%" pitch="0%">你可将此文本替换为所需的任何文本。你可在此文本框中编写或在此处粘贴你自己的文本。

    # 试用不同的语言和声音。改变语速和音调。你甚至可调整 SSML（语音合成标记语言），以控制文本不同部分的声音效果。单击上面的 SSML 试用一下！

    # 请尽情使用文本转语音功能！</prosody></voice></speak>"""
    #                 )
    #                 self.flag = True

    #   文字转语音
    def text_to_speech(self, text: str):
        if not self.ws:
            self.connect_ws()

        requestId = self.requestId
        self.now_request = requestId
        now = self.now_time
        payload = f"""Path: speech.config
X-RequestId: {requestId}
X-Timestamp: {now}
Content-Type: application/json

{json.dumps(self.platform,separators=(',', ':'))}"""
        self.ws.send(payload)
        payload = f"""Path: synthesis.context
X-RequestId: {requestId}
X-Timestamp: {now}
Content-Type: application/json

{json.dumps(self.voice,separators=(',', ':'))}"""
        self.ws.send(payload)
        payload = f"""Path: ssml
X-RequestId: {requestId}
X-Timestamp: {now}
Content-Type: application/ssml+xml

<speak xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="http://www.w3.org/2001/mstts" xmlns:emo="http://www.w3.org/2009/10/emotionml" version="1.0" xml:lang="en-US"><voice name="zh-CN-XiaoxiaoNeural"><prosody rate="0%" pitch="0%">{text}</prosody></voice></speak>"""
        self.ws.send(payload)
        data = self.ws.recv()
        print(data)

    #   异步文字转语音
    async def text_to_speech_async(self, text: str):
        if not self.ws:
            await self.async_connect_ws()

        requestId = self.requestId
        self.now_request = requestId
        now = self.now_time
        payload = f"""Path: speech.config\r\nX-RequestId: {requestId}\r\nX-Timestamp: {now}\r\nContent-Type: application/json\r\n\r\n{json.dumps(self.platform,separators=(',', ':'))}"""
        await self.ws.send(payload)
        payload = f"""Path: synthesis.context\r\nX-RequestId: {requestId}\r\nX-Timestamp: {now}\r\nContent-Type: application/json\r\n\r\n{json.dumps(self.voice,separators=(',', ':'))}"""
        await self.ws.send(payload)
        payload = f"""Path: ssml\r\nX-RequestId: {requestId}\r\nX-Timestamp: {now}\r\nContent-Type: application/ssml+xml\r\n\r\n<speak xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="http://www.w3.org/2001/mstts" xmlns:emo="http://www.w3.org/2009/10/emotionml" version="1.0" xml:lang="en-US"><voice name="zh-CN-XiaoxiaoNeural"><prosody rate="0%" pitch="0%">{text}</prosody></voice></speak>"""
        await self.ws.send(payload)

    #   监听消息
    async def listen(self):
        while True:
            msg = await self.ws.recv()
            print(msg)
            self.parse_audio({"data": msg, "requestId": self.now_request})
            # try:
            # except websockets.exceptions.ConnectionClosed as e:
            #     print("Connection closed")
            #     print(e)
            #     break

    #   声音消息解析
    def parse_audio(self, params: dict):
        if not params:
            return

        data = params.get("data", b"")
        requestId = params.get("requestId")

        if isinstance(data, bytes):
            #   解析数据
            header_len = 130
            start_byte = b"\x00\x80"
            request_byte = data[
                len(start_byte) : len(f"X-RequestId:{requestId}") + len(start_byte)
            ]
            contentType_byte = data[48:71]
            streamId_byte = data[73:116]
            path_type = data[118:128]

            #   添加数据
            if not self.audio_map.get(requestId):
                self.audio_map.setdefault(requestId, [])

            body = data[header_len:]
            if body:
                self.audio_map[requestId].append(body)
        elif isinstance(data, str):
            if data.find("end") != -1:
                self.play_audio(self.now_request)
                return

    #   播放声音
    def play_audio(self, requestId: str):
        audio_data = b"".join(self.audio_map.get(requestId, []))
        # winsound.PlaySound(audio_data, winsound.SND_MEMORY)
        # with open(r"C:\Users\scp\Desktop\test.mp3", "wb") as f:
        with open("./test.wav", "wb") as f:
            f.write(audio_data)
        # audio = pyaudio.PyAudio()
        # stream = audio.open(format=pyaudio.paInt16, channels=1, rate=16000, output=True)
        # stream.write(audio_data)
        # dt = sa.play_buffer(audio_data, 2, 3, 44100)
        # sd.OutputStream(
        #     samplerate=44100, blocksize=1024, device=0, fs=audio_data
        # ).start()
        # playsound(audio_data)
        # playsound("./test.wav")


if __name__ == "__main__":
    client = TTS()

    # client.connect_websocket()
    # client.text_to_speech("测试")
    loop = asyncio.get_event_loop()
    conn = loop.run_until_complete(client.async_connect_ws())
    tasks = [
        asyncio.ensure_future(client.listen()),
        asyncio.ensure_future(client.text_to_speech_async("竟然没有一个能用的包")),
    ]
    loop.run_until_complete(asyncio.wait(tasks))
