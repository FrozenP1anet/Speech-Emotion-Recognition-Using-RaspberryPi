import serial
import threading

def uart_init(uart_dev_path, uart_baud, timeout=2):
    """ UART初始化 """
    ser = serial.Serial(uart_dev_path, uart_baud, timeout=2)    # 设置接收超时时间为2s
    return ser


def uart_send_cmd(ser, cmd):
    """ UART发送串口屏命令字符串 """
    data_send = cmd
    bytes_send = data_send.encode('utf-8') + b'\xFF\xFF\xFF'
    ser.write(bytes_send)


def uart_rcv_cmd(ser):
    """ UART接收串口屏发送的字符串，以\n结尾，一直等待 """
    return ser.readline().decode('utf-8').strip()


# UART接收线程全局变量
return_main_page = False        # 串口屏是否返回主页面
uart_exit_flag = False          # 主线程通知子线程是否退出
data_lock = threading.Lock()    # 全局变量互斥锁

def uart_rcv_cmd_thread(ser):
    """ 用于UART接收线程 """
    global return_main_page
    global uart_exit_flag

    while not uart_exit_flag:
        # print('Enter uart_rcv_cmd_thread!')
        uart_rcv_cmd = ser.readline().decode('utf-8').strip()
        if uart_rcv_cmd == 'return_main_page':
            with data_lock:
                return_main_page = True
