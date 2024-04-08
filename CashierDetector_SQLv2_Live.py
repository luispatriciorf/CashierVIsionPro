from ultralytics import YOLO
import cv2
import cvzone
import math
import numpy as np
from sort import *
import datetime
from datetime import datetime, timedelta
#from urllib.parse import quote_plus
import time
import mysql.connector
from mysql.connector import Error

class cashierless:
    def __init__(self):
        # Load the YOLO model created from main.py - change text to your relative path
        #self.model = YOLO("Yolov8X12ProductsNewAdded.pt")
        self.model = YOLO("Yolov8X12ProductsNewAdded2.pt")
        #self.model = YOLO("Yolov8X12Products.pt")
        #self.class_names = ['canbeans', 'coffeenescafe', 'coke', 'jelly', 'nutella', 'oreopack', 'peanutbutter']

        self.class_names = [
            "barsoap",
            "canbeans",
            "coffeenescafe",
            "coke",
            "hotchocolate",
            "jelly",
            "nutella",
            "oreopack",
            "peanutbutter",
            "pizzabox",
            "teabox",
            "tomatosauce"
        ]
        
        self.classnames = self.class_names

        # Use video - replace text with your video path
        # D:\My_St_Clair_College\Other_projects\CollegeCapstone\CashierLess\Files\VideoTestings
        #self.cap = cv2.VideoCapture(0)
        self.cap = cv2.VideoCapture(r'Files\VideoTestings\SecondTesting\2same_1.mp4')
        #self.cap = cv2.VideoCapture(r'Files\VideoTestings\FirstTesting\merge2videos.mp4')

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1080)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1920)

        self.frame_count = 0
        self.frame = None

        self.tracker = Sort(max_age=50, min_hits=5)
        #self.treadmill_rect = [50, 200, 400, 500]  # Coordenadas del rectángulo de la treadmill video test
        #self.treadmill_rect = [50, 200, 350, 300]  # video capture only [,w,h]
        #self.treadmill_rect = [50, 80, 350, 200]  # live from the front
        self.treadmill_rect = [600, 100, 800, 700]  # live from the side

        self.detected_products = {}  # Diccionario para almacenar los productos detectados y sus detalles
        
        # List to store IDs of products that have been registered
        self.registered_product_ids = []
        self.last_detection_time = None

        # Contador de productos dentro del rectángulo de la cinta transportadora
        self.products_inside_treadmill = 0

        self.detected_products_count = {}
        self.data_sent = False

        self.run()

    def run(self):
        while True:
            ret, self.frame = self.cap.read()
            detections = np.empty((0, 5))
            if not ret:
                break
            
            # Desactiva el enfoque automático
            self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        
            # Establece el valor de enfoque manual (puedes ajustarlo según sea necesario)
            self.cap.set(cv2.CAP_PROP_FOCUS, 0)  # 0 indica el enfoque más cercano

            self.frame = cv2.convertScaleAbs(self.frame, alpha=0.6, beta=10)
            # Girar el fotograma 90 grados en sentido antihorario (sentido contrario a las agujas del reloj)
            #self.frame = cv2.rotate(self.frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

            top_bar = (0, 0, self.frame.shape[1], 150)  # (x1, y1, x2, y2)
            bottom_bar = (0, self.frame.shape[0] - 150, self.frame.shape[1], self.frame.shape[0])

            # Add the black bars to the frame
            cv2.rectangle(self.frame, (top_bar[0], top_bar[1]), (top_bar[2], top_bar[3]), (0, 0, 0), -1)  # Top black bar
            cv2.rectangle(self.frame, (bottom_bar[0], bottom_bar[1]), (bottom_bar[2], bottom_bar[3]), (0, 0, 0), -1)  # Bottom black bar

            res = self.model(self.frame, stream=1)

            for info in res:
                param = info.boxes
                for details in param:
                    x1, y1, x2, y2 = details.xyxy[0]
                    conf = details.conf[0]
                    conf = math.ceil(conf * 100)
                    class_detection = details.cls[0]
                    class_detect = int(class_detection)
                    class_detect = self.classnames[class_detect]

                    if conf > 70:
                        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                        current_detect = np.array([x1, y1, x2, y2, conf])
                        detections = np.vstack((detections, current_detect))
                        cvzone.cornerRect(self.frame, [x1, y1, x2 - x1, y2 - y1], rt=1, colorC=(173, 216, 230), t=1, colorR=(173, 216, 230))
                        cvzone.putTextRect(self.frame, f'{class_detect} {conf}', [x1 + 8, y1 - 12], scale=1, thickness=1, border=1, colorB=(0, 216, 230), colorR=(255, 100, 100))
                        self.last_detection_time = time.time()

            results = self.tracker.update(detections)

            cv2.rectangle(self.frame, (self.treadmill_rect[0], self.treadmill_rect[1]), (self.treadmill_rect[2], self.treadmill_rect[3]), (0, 216, 230), 2)  # Dibuja el rectángulo de la treadmill
            
            products_detected = False

            for info in results:
                x1, y1, x2, y2, id = info
                x1, y1, x2, y2, id = int(x1), int(y1), int(x2), int(y2), int(id)
                w, h = x2 - x1, y2 - y1
                cx, cy = x1 + w // 2, y1 + h // 2  # Calculate the center coordinates
                
                if self.object_in_treadmill([cx, cy], self.treadmill_rect):  # Check if center coordinates are within treadmill rectangle
                    products_detected = True
                    product_id = f"{class_detect}_{id}"  # Unique ID for the product instance
                    print(product_id)
                    self.products_inside_treadmill += 1

                    # Verifica si el producto ya ha sido contabilizado
                    if product_id in self.detected_products_count:
                        # Si ya ha sido contabilizado, incrementa el contador
                        self.detected_products_count[product_id] += 1
                    else:
                        # Si es la primera vez que se detecta, inicializa el contador en 1
                        self.detected_products_count[product_id] = 1

                    # Check if the product instance has already been registered
                    if product_id not in self.registered_product_ids:
                        self.registered_product_ids.append(product_id)  # Add the ID to the list of registered IDs

                        #class_detect = self.classnames[id]
                        # Retrieve unit price, id image, and real name based on class detection
                        unit_price = None
                        id_image = None
                        real_name = None

                        if class_detect == "coke":
                            unit_price = 0.57
                            buy_price = 0.26
                            id_image = "1"
                            real_name = "Coca-Cola"
                        elif class_detect == "coffeenescafe":
                            unit_price = 4.94
                            buy_price = 2.58
                            id_image = "2"
                            real_name = "Nescafe"
                        elif class_detect == "nutella":
                            unit_price = 5.47
                            buy_price = 3.58
                            id_image = "3"
                            real_name = "Nutella"
                        elif class_detect == "oreopack":
                            unit_price = 3.48
                            buy_price = 1.27
                            id_image = "4"
                            real_name = "Oreo Pack"
                        elif class_detect == "canbeans":
                            unit_price = 1.47
                            buy_price = 0.50
                            id_image = "5"
                            real_name = "Can Beans"
                        elif class_detect == "peanutbutter":
                            unit_price = 3.99
                            buy_price = 2.67
                            id_image = "6"
                            real_name = "Peanut Butter"
                        elif class_detect == "jelly":
                            unit_price = 1.27
                            buy_price = 0.35
                            id_image = "7"
                            real_name = "Jello"
                            #-------------------------
                        elif class_detect == "barsoap":
                            unit_price = 1.23
                            buy_price = 0.00
                            id_image = "8"
                            real_name = "Bar Soap"
                        elif class_detect == "hotchocolate":
                            unit_price = 6.27
                            buy_price = 3.15
                            id_image = "9"
                            real_name = "Hot Chocolate"
                        elif class_detect == "pizzabox":
                            unit_price = 21.19
                            buy_price = 10.99
                            id_image = "10"
                            real_name = "Pizza Box"
                        elif class_detect == "teabox":
                            unit_price = 2.29
                            buy_price = 1.56
                            id_image = "11"
                            real_name = "Tea Box"
                        elif class_detect == "tomatosauce":
                            unit_price = 2.99
                            buy_price = 0.80
                            id_image = "12"
                            real_name = "Tomato Sauce"
                            
                        # Get the current date and time
                        date = datetime.now()

                        # Register the product with all necessary information including the date
                        self.register_product(class_detect, unit_price, buy_price, id_image, date)
                        #print(f'Class: {class_detect}, Unit_Price: {unit_price}, Id_imagei{id_image}, Date: {date}')
                    
                    cv2.rectangle(self.frame, (self.treadmill_rect[0], self.treadmill_rect[1]), (self.treadmill_rect[2], self.treadmill_rect[3]), (0, 0, 230), 2)  # Dibuja el rectángulo de la treadmill

            if not products_detected and self.last_detection_time is not None:
                if time.time() - self.last_detection_time > 5 and not self.data_sent:
                    # Solo inserta datos en la base de datos si no se detectan productos dentro de la cinta transportadora
                    # durante un período de tiempo específico después de la última detección
                    self.insert_data_into_db(self.detected_products)
                    self.detected_products = {}  # Limpia las detecciones almacenadas
                    self.data_sent = True
            
            elif products_detected:
                # Si se detectan nuevos productos, restablecer la bandera data_sent
                self.data_sent = False

            cvzone.putTextRect(self.frame, f'Products: {list(set(self.detected_products))}', [50, 34], thickness=2, scale=1, border=1, colorR=(255, 100, 100), colorB=(255, 100, 100))
            cvzone.putTextRect(self.frame, f'Total: {len(self.detected_products)}', [50, 54], thickness=2, scale=1, border=1, colorR=(255, 100, 100), colorB=(255, 100, 100))

            #self.out.write(self.frame)
            cv2.imshow('Frame', self.frame)

            # Close if 'q' is clicked
            if cv2.waitKey(1) & 0xFF == ord('q'):  # higher waitKey slows video down, use 1 for webcam
                break
        
        print(set(self.detected_products))
        self.insert_data_into_db(self.detected_products)
        self.cap.release()
        cv2.destroyAllWindows()

    def object_in_treadmill(self, center_coords, treadmill_rect):
        cx, cy = center_coords
        x1_treadmill, y1_treadmill, x2_treadmill, y2_treadmill = treadmill_rect

        if x1_treadmill < cx < x2_treadmill and y1_treadmill < cy < y2_treadmill:
            return True
        else:
            return False

    def register_product(self, class_detect, unit_price, buy_price, id_image, date):
        # Verifica si el producto ya está en el diccionario de productos detectados
        if class_detect in self.detected_products:
            # Si el producto ya está en el diccionario, actualiza los detalles de la última detección
            self.detected_products[class_detect][-1] = {'unit_price': unit_price, 'buy_price': buy_price, 'id_image': id_image, 'date': date}
        else:
            # Si el producto no está en el diccionario, agrega una nueva instancia
            self.detected_products[class_detect] = [{'unit_price': unit_price, 'buy_price': buy_price, 'id_image': id_image, 'date': date}]
            
    def insert_data_into_db(self, detected_products):
        # MySQL Connection Setup
        username = 'cashierv_pramirez'
        password = 'pramirez2024!'
        host = '154.53.34.93'
        database = 'cashierv_wp257'

        try:
            connection = mysql.connector.connect(
                host=host,
                database=database,
                user=username,
                password=password)
            
            if connection.is_connected():
                print("Connected to MySQL database")

                # Insert data into the MySQL database
                cursor = connection.cursor()

                for product, instances in detected_products.items():
                    for instance in instances:
                        class_detect = product
                        unit_price = instance['unit_price']  # Access unit_price directly from instance
                        buy_price = instance['buy_price']
                        id_picture = instance['id_image']
                        date = instance['date']

                        sql_query = "INSERT INTO billprocess (product_name, unit_price, buy_price, id_picture, date) VALUES (%s, %s, %s, %s, %s)"
                        data = (class_detect, unit_price, buy_price, id_picture, date)

                        cursor.execute(sql_query, data)

                connection.commit()
                print("Data inserted successfully into MySQL database")

        except Error as e:
            print("Error while connecting to MySQL or inserting data:", e)

        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
                print("MySQL connection is closed")



if __name__ == "__main__":
    cashierless()
