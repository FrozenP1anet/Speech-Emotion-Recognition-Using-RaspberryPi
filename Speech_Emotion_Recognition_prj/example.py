import os
import threading
import LED_ctrl
import uart_ctrl
import my_module
import audio_collect
import debug

# 初始化LED
LED_COUNT = 1        # LED数量
LED_PIN = 18         # GPIO引脚号(BCM编号)
LED_BRIGHTNESS = 255 # 亮度
strip = LED_ctrl.LED_init(LED_COUNT, LED_PIN, LED_BRIGHTNESS)
LED_ctrl.LED_turn_off(strip)
# 初始化UART
uart_dev_path = '/dev/serial1'
uart_baud = 115200
ser = uart_ctrl.uart_init(uart_dev_path, uart_baud)
# uart_cmd_send = 'volume=50'          
# uart_ctrl.uart_send_cmd(ser, uart_cmd_send)
# get ip address
wlan_ip = debug.get_ip_address(interface='wlan0')
uart_cmd_send = f't2.txt=\"IP={wlan_ip}\"'
uart_ctrl.uart_send_cmd(ser, uart_cmd_send)
# 配置采样参数
sample_duration = 6
sample_rate = 48000
sample_format = "int16"
# 配置VAD模式
VAD_mode = 1
# 配置文件夹路径
directory_path = "./my_audios/chunk"
opensmile_path = '/home/pi/opensmile-3.0.2'
# 加载模型
model_path = './models'
model_name = 'LSTM_OPENSMILE_IS10'
model = my_module.model_load(model_path, model_name)
# 初始化结束
print('Initialize Finished.')
uart_cmd_send = 'progress_bar_val=100'          # 将串口屏首页加载进度条的值设为100
uart_ctrl.uart_send_cmd(ser, uart_cmd_send)

while True:
    # 等待串口屏进入page1
    while True:
        uart_cmd_rcv = uart_ctrl.uart_rcv_cmd(ser)
        if uart_cmd_rcv == 'enter_page1':
            break

    # 创建UART接收线程，用于接收退出信号
    uart_rcv_thread = threading.Thread(target=uart_ctrl.uart_rcv_cmd_thread, args=(ser,))
    uart_ctrl.uart_exit_flag = False
    uart_rcv_thread.start()

    # 心情指示条h0.val
    h0_val = 70
    LED_rainbow_thread_deleted = True
    
    while True:
        if LED_rainbow_thread_deleted:
            # 创建LED全彩灯线程，用于指示正在监听麦克风信号
            LED_rainbow_thread = threading.Thread(target=LED_ctrl.LED_rainbow_thread, args=(strip, 100))
            LED_ctrl.LED_exit_flag = False
            LED_rainbow_thread.start()
            LED_rainbow_thread_deleted = False
        # 采集音频
        audio_data = audio_collect.voice_trigger(sample_duration, sample_rate, sample_format)
        audio_data_pcm = audio_data.tobytes()
        # 串口接收到'return_main_page'，退出循环
        if uart_ctrl.return_main_page:
            break
        # VAD获取有语音的部分
        audio_collect.VAD(audio_data_pcm, sample_rate, VAD_mode)
        # 读取文件夹下的所有文件
        file_names = [f for f in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, f))]
        # 采集到有效音频信号，则删除LED全彩灯线程
        if file_names != []:
            LED_ctrl.LED_exit_flag = True
            LED_rainbow_thread.join()
            LED_rainbow_thread_deleted = True
            LED_ctrl.LED_turn_off(strip)

        # 处理有效音频信号
        for file_name in file_names:
            audio_path = os.path.join(directory_path, file_name)
            print("Processing %s..." % audio_path)
            # 模型预测
            result = my_module.model_predict(audio_path, opensmile_path, model)
            # 心情指示条h0变化
            if result == 'angry' or result == 'sad' or result == 'fear':
                h0_val -= 10
                if h0_val < 0:
                    h0_val = 0
            else:
                h0_val += 10
                if h0_val > 100:
                    h0_val = 100
            uart_cmd_send = f'h0.val={h0_val}'
            uart_ctrl.uart_send_cmd(ser, uart_cmd_send)
            # LED呼吸灯指示
            LED_ctrl.LED_change(result, strip)
            break

        # 串口接收到'return_main_page'，退出循环
        if uart_ctrl.return_main_page:
            break
    
    # 删除UART接收线程
    uart_ctrl.uart_exit_flag = True
    uart_rcv_thread.join()
    # 删除LED全彩灯线程
    if LED_rainbow_thread_deleted == False:
        LED_ctrl.LED_exit_flag = True
        LED_rainbow_thread.join()
        LED_rainbow_thread_deleted = True
        LED_ctrl.LED_turn_off(strip)
    print('Return to main page.')
    uart_ctrl.return_main_page = False
