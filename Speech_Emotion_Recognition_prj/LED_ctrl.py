import time
import math
from rpi_ws281x import Adafruit_NeoPixel, Color

def LED_init(LED_COUNT, LED_PIN, LED_BRIGHTNESS, LED_FREQ_HZ = 800000, LED_DMA = 10, LED_INVERT = False):
    """ LED灯带初始化 """
    strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS)
    strip.begin()
    return strip


def LED_turn_off(strip):
    """ 熄灭LED灯带 """
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0, 0, 0))  # 设置颜色为黑色
    strip.show()


def wheel(pos):
    """生成横跨0-255个位置的彩虹颜色."""
    if pos < 85:
        return Color(pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return Color(255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return Color(0, pos * 3, 255 - pos * 3)
    

# LED全彩灯线程全局变量
LED_exit_flag = False

def LED_rainbow_thread(strip, brightness):
    """绘制彩虹，所有色彩显示一次."""
    global LED_exit_flag

    wait_time = 20      # 一种颜色的停留时间20ms
    while True:
        for j in range(256):
            # brightness_set = min(int((1 - math.cos(j/256*2*math.pi)) * brightness / 2), 255)
            brightness_set = min(int(min(256-j, j)*brightness/128), 255)
            for i in range(strip.numPixels()):
                strip.setPixelColor(i, wheel((i + j) & 255))
                strip.setBrightness(brightness_set)
            strip.show()
            time.sleep(wait_time / 1000.0)
            if LED_exit_flag:
                break
        if LED_exit_flag:
            break


def LED_breathe(strip, color, breathing_time):
    """ LED呼吸灯 """
    total_steps = 100
    sleep_time = breathing_time / total_steps

    for i in range(total_steps):
        brightness = min(int((1 - math.cos(i / 50 * math.pi)) * 128), 255)
        strip.setPixelColor(0, color)
        strip.setBrightness(brightness)
        strip.show()
        time.sleep(sleep_time)
    

def LED_change(result, strip):
    """ 根据结果改变LED的色彩 """
    if result == 'angry':
        cnt = 4
        while cnt:
            LED_breathe(strip, Color(255, 0, 0), 2)
            cnt -= 1
    elif result == 'sad':
        cnt = 3
        while cnt:
            LED_breathe(strip, Color(0, 0, 255), 4)
            cnt -= 1
    elif result == 'fear':
        cnt = 3
        while cnt:
            LED_breathe(strip, Color(0, 255, 0), 3)
            cnt -= 1
    else:
        cnt = 3
        while cnt:
            LED_breathe(strip, Color(255, 255, 255), 3)
            cnt -= 1
