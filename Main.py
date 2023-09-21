import math
import time
import cv2
import torch
from ultralytics import YOLO
import serial

# region Methods
def check_com(com):                 # Not use
    com.write(b'AT\r\n')
    response = com.readline()
    if response.strip() == b'OK':
        print('COM ok')
    else:
        print('COM Disconnect')
# endregion

# ----------COM---------------------
port = 'COM2'
baudrate = 9600
parity = serial.PARITY_NONE
bytesize = 8
stopbits = 1
# ---------------------------------

classNames = ["person", "bicycle", "car", "motorbike", "aeroplane", "bus", "train", "truck", "boat",
              "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
              "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella",
              "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball", "kite", "baseball bat",
              "baseball glove", "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup",
              "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange", "broccoli",
              "carrot", "hot dog", "pizza", "donut", "cake", "chair", "sofa", "pottedplant", "bed",
              "diningtable", "toilet", "tvmonitor", "laptop", "mouse", "remote", "keyboard", "cell phone",
              "microwave", "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase", "scissors",
              "teddy bear", "hair drier", "toothbrush"
              ]


# ----------Fields---------------------
run = False
cap = cv2.VideoCapture(0)
model = YOLO("yolov8n.pt")

com_port = serial.Serial(port, baudrate, bytesize, parity, stopbits)
com_port.close()

recv_count =0
send_count =0
# ---------------------------------

while True:
    # Exit Program by click Esc
    if cv2.waitKey(1) == 27:
        break

    # Open COM and wait run command
    if not com_port.is_open:
        com_port.open()

    # Read COM Data
    if com_port.in_waiting > 0:
        buff = com_port.readline()
        print(buff)
        cmd = buff.decode().strip()
        print(cmd)
        if cmd == 'start':      # Start detect command
            run = True
        elif cmd == 'stop':     # Stop detect command
            run = False
        elif cmd == 'OK':       # Rep from C# -> nhận xong trả OK
            recv_count +=1

    # Run
    ret, frame = cap.read()
    if run:
        #check connect nếu số lần gửi nếu gửi - nhận > 100 -> báo error -> stop detect
        if abs(recv_count - send_count) > 100:
            print('COM communication error')
            recv_count =0
            send_count =0
            run = False

        results = model.predict(frame)
        result = results[0]
        
        if not ret: 
            print('Camera capture fail')
            continue

        # Draw all vật thể detect được
        for box in result.boxes:
            x1, y1, x2, y2 = box.xyxy[0]
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
            conf = math.ceil((box.conf[0] * 100)) / 100
            cls = int(box.cls[0])
            class_name = classNames[cls]
            label = f'{class_name}{conf}'
            t_size = cv2.getTextSize(label, 0, fontScale=1, thickness=2)[0]
            # print(t_size)
            c2 = x1 + t_size[0], y1 - t_size[1] - 3
            cv2.rectangle(frame, (x1, y1), c2, [0, 0, 255], -1, cv2.LINE_AA)  # filled
            cv2.putText(frame, label, (x1, y1 - 2), 0, 1, [255, 255, 255], thickness=1, lineType=cv2.LINE_AA)

        # Kiểm tra vật thể có score cao nhất nếu là người or phone và score > 0.75 gửi data ra C#
        if len(result.boxes) > 0:
            max_value, max_idx = torch.max(result.boxes.conf, dim=0)
            box = result.boxes[max_idx]
            # Draw bbox
            x1, y1, x2, y2 = box.xyxy[0]
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            print(x1, y1, x2, y2)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 3)
            conf = math.ceil((box.conf[0] * 100)) / 100
            cls = int(box.cls[0])
            class_name = classNames[cls]
            label = f'{class_name}{conf}'
            # Frame format: (\0Name,score,X1,Y1,X2,Y2\r)
            if class_name == "person" and conf > 0.75:

                data = f"\x00{class_name},{conf},{x1},{y1},{x2},{y2}\x0D".encode()
                # x_center1 = (x1 + x2) // 2
                # y_center1 = (y1 + y2) // 2
                # Persion_Object = 1
                # data = f"{Persion_Object},{x_center1},{y_center1}".encode()
                # Gửi data to COM
                if not com_port.is_open:
                    com_port.open()
                com_port.write(data)
                send_count += 1
                print(f"Đã gửi dữ liệu ra cổng {com_port.port}: {data}")
            elif  class_name == "cell phone" and conf > 0.75:
                data = f"\x00{class_name},{conf},{x1},{y1},{x2},{y2}\x0D".encode()
                if not com_port.is_open:
                    com_port.open()
                com_port.write(data)
                send_count += 1
                print(f"Đã gửi dữ liệu ra cổng {com_port.port}: {data}")
            else:
                data = f"\x00{'Empty'},{0},{0},{0},{0},{0}\x0D".encode()
                # x_center1 = (x1 + x2) // 2
                # y_center1 = (y1 + y2) // 2
                # Persion_Object = 2
                # data = f"{Persion_Object},{x_center1},{y_center1}".encode()
                if not com_port.is_open:
                    com_port.open()
                com_port.write(data)
                send_count += 1
                print(f"Đã gửi dữ liệu ra cổng {com_port.port}: {data}")
            # time.sleep(0.5)
        else:
            data = f"\x00{'Empty'},{0},{0},{0},{0},{0}\x0D".encode()
            # data = f"{0},{0},{0}".encode()
            if not com_port.is_open:
                        com_port.open()
            com_port.write(data)

    cv2.imshow("Frame", frame)

com_port.close()
cap.release()
cv2.destroyAllWindows()

