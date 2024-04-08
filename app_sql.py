from flask import Flask, render_template, request, session, url_for, redirect
from datetime import datetime
from io import BytesIO
import base64
import qrcode
from mysql.connector import Error
import mysql.connector
import uuid

app = Flask(__name__)
app.secret_key = 'cashiervisionpro'
last_check_date = None

username = 'cashierv_pramirez'
password = 'pramirez2024!'
host = '154.53.34.93'
database = 'cashierv_wp257'

usuarios = {
    '001': 'USER 001',
    '002': 'USER 002',
    '003': 'USER 003'
}

@app.route('/checkout')
def checkout():
    global last_check_date

    try:
        connection = mysql.connector.connect(
            host=host,
            database=database,
            user=username,
            password=password)
        
        if connection.is_connected():
            print("Connected to MySQL database")

    except Error as e:
        print("Error while connecting to MySQL", e)

    #try:
    if connection.is_connected():
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM billprocess")
        products = cursor.fetchall()
        
        unique_products = {}
        new_products_in_current_cycle = []
        code_images = {}
        
        for product in products:
            product_name = product[0]
            unit_price = product[1]
            #buy_price = product[2]
            id_picture = product[3]
            date = product[4]
            #print("Date from database:", date)
            if product_name not in unique_products:
                unique_products[product_name] = {   
                    'quantity': 1,
                    'total_price': unit_price,
                    'id_picture': id_picture
                }
                
                if last_check_date and last_check_date < date:
                    
                    new_products_in_current_cycle.append(product_name)
            else:
                unique_products[product_name]['quantity'] += 1
                unique_products[product_name]['total_price'] += unit_price

            # Fetch image data
            cursor.execute("SELECT code FROM product_images WHERE id_picture = %s", (id_picture,))
            image_data = cursor.fetchone()

            if image_data:
                # Decode the binary image
                image_binary = image_data[0]
                # Store the image binary in the product
                code_images[id_picture] = base64.b64encode(image_binary).decode('utf-8')
            else:
                # Handle case when no image data is found
                code_images[id_picture] = None

        last_check_date = datetime.now()

        # Update product data with base64 encoded images
        for product_name, product_data in unique_products.items():
            id_picture = product_data['id_picture']
            if id_picture in code_images and code_images[id_picture] is not None:
                # Store the base64 encoded image in product data
                product_data['code_image'] = code_images[id_picture]

        total_sum = sum(product_data['total_price'] for product_data in unique_products.values())
        session['total_sum'] = total_sum

        return render_template('checkout.html', unique_products=unique_products, new_products=new_products_in_current_cycle, total_sum=total_sum)
    #except Error as e:
    #    print("Error while fetching data from MySQL", e)

    #return "Error fetching data from MySQL"

@app.route('/update_checkout')
def update_checkout():
    # Esta función se llama para obtener una actualización del HTML de la página de checkout.        
    return checkout()

@app.route('/', methods=['GET', 'POST'])
def ingresar_id():
    error_message = None
    nombre_usuario = None
    
    if request.method == 'POST':
        id_comprador = request.form.get('id_comprador')
        nombre_usuario = usuarios.get(id_comprador)
        if nombre_usuario:
            session['id_entering'] = id_comprador
            return render_template('home.html', nombre_usuario=nombre_usuario)
        else:
            error_message = "Invalid ID, please try again."

    

    # Si el método de solicitud es GET o si el ID es inválido, mostrar el formulario de ingreso de ID
    return render_template('id_entering.html', error_message=error_message)

@app.route('/delete_product', methods=['GET'])
def delete_product():
    product_name = request.args.get('product')

    try:
        connection = mysql.connector.connect(
            host=host,
            database=database,
            user=username,
            password=password)
        
        if connection.is_connected():
            print("Connected to MySQL database")

    except Error as e:
        print("Error while connecting to MySQL", e)
        
    #try:
    if connection.is_connected():
        cursor = connection.cursor()

        # Encontrar y eliminar el primer registro que coincide con el nombre del producto
        cursor.execute("DELETE FROM billprocess WHERE product_name = %s LIMIT 1", (product_name,))
        connection.commit()

        return checkout()

@app.route('/qr_code')
def show_qr_code():
    total_sum = session.get('total_sum')

    # URL a la página que genera la imagen PNG
    purchase_image_url = "https://cashiervision.pro/thankyou/"
    #purchase_details_url = 'http://127.0.0.1:5000/product_details'

    # Construir el texto del código QR con la URL
    #qr_text = "View Purchase Image: {purchase_image_url}"

    # Generar el código QR
    qr = qrcode.QRCode(
        version=3,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(purchase_image_url)
    qr.make(fit=False)

    # Generar la imagen del código QR y devolverla al cliente
    img = qr.make_image(fill_color="black", back_color="white")
    img_io = BytesIO()
    img.save(img_io, format='PNG')
    img_io.seek(0)
    img_base64 = base64.b64encode(img_io.getvalue()).decode()
    
    try:
        connection = mysql.connector.connect(
            host=host,
            database=database,
            user=username,
            password=password)
        
        if connection.is_connected():
            print("Connected to MySQL database")

    except Error as e:
        print("Error while connecting to MySQL", e)

    if connection.is_connected():
        cursor = connection.cursor()

        cursor.execute("SELECT * FROM billprocess")
        products = cursor.fetchall()

        historical_collection = []

        # Generate a unique purchase ID
        purchase_id = str(uuid.uuid4())

        id_entering = session.get('id_entering')
        #print(id_entering)
        for product in products:
            # Append the purchase ID to each record
            product_with_id = list(product)
            product_with_id.append(purchase_id)
            product_with_id.append(id_entering)
            historical_collection.append(tuple(product_with_id))

        if historical_collection:
            cursor.executemany("INSERT INTO historicalpurchases (product_name, unit_price, buy_price, id_picture, date, id_purchase, id_entering) VALUES (%s, %s, %s, %s, %s, %s, %s)", historical_collection)
            connection.commit()
            
        cursor.execute("DELETE FROM billprocess")
        connection.commit()
        
    return render_template('qr_code.html', qr_code=img_base64)

@app.route('/cancel_purchase', methods=['GET'])
def cancel_purchase():
    try:
        connection = mysql.connector.connect(
            host=host,
            database=database,
            user=username,
            password=password)
        
        if connection.is_connected():
            cursor = connection.cursor()
            # Eliminar todos los elementos de la tabla billprocess
            cursor.execute("DELETE FROM billprocess")
            connection.commit()
            return "Purchase cancelled successfully"
    except Error as e:
        print("Error while cancelling purchase:", e)
        return "Error cancelling purchase"

    return "Error cancelling purchase"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=True)
