from flask import Flask, render_template, request, redirect, url_for
import requests
import os
from dotenv import load_dotenv
import re

load_dotenv()

app = Flask(__name__)

API_KEY = os.getenv('GOOGLE_BOOKS_API_KEY')


ultimos_libros = []
ultimos_autores = []

MAX_ULTIMOS_LIBROS = 5
MAX_ULTIMOS_AUTORES = 3

def eliminar_etiquetas_html(texto):
    return re.sub('<.*?>', '', texto)

def buscar_libros_por_autor(api_key, autor, start_index=0, max_results=20):
    url = f"https://www.googleapis.com/books/v1/volumes?q=inauthor:{autor}&startIndex={start_index}&maxResults={max_results}&key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": response.json()}

def buscar_libros_por_titulo(api_key, titulo, max_results=20):
    url = f"https://www.googleapis.com/books/v1/volumes?q=intitle:{titulo}&maxResults={max_results}&key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": response.json()}

def agregar_a_ultimos_libros(libros):
    global ultimos_libros
    ids_existentes = {libro['id'] for libro in ultimos_libros}
    for libro in libros:
        if libro['id'] not in ids_existentes:
            ultimos_libros.insert(0, libro)
            ids_existentes.add(libro['id'])
            if len(ultimos_libros) > MAX_ULTIMOS_LIBROS:
                ultimos_libros.pop()

def agregar_a_ultimos_autores(autor):
    global ultimos_autores
    if autor not in ultimos_autores:
        ultimos_autores.insert(0, autor)
        if len(ultimos_autores) > MAX_ULTIMOS_AUTORES:
            ultimos_autores.pop()

def obtener_info_autor(api_key, autor):
    libros = buscar_libros_por_autor(api_key, autor, max_results=5)
    if "items" in libros:
        libro = libros["items"][0]
        descripcion = eliminar_etiquetas_html(libro['volumeInfo'].get('description', 'No se encontró una descripción del autor.'))
        imagen = libro["volumeInfo"]["imageLinks"].get("thumbnail", None) if "imageLinks" in libro["volumeInfo"] else None
        return {"descripcion": descripcion, "imagen": imagen, "libros": libros["items"]}
    return {"descripcion": "No se encontró información del autor.", "imagen": None, "libros": []}

def clasificar_edad(maturity_rating):
    if maturity_rating == 'NOT_MATURE':
        return 'Juvenil'
    elif maturity_rating == 'MATURE' or maturity_rating == 'FOR_MATURE_AUDIENCES':
        return 'Adulto'
    else:
        return 'No especificado'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/buscar_libros')
def buscar_libros():
    return render_template('buscar_libros.html', ultimos_libros=ultimos_libros, ultimos_autores=ultimos_autores)

@app.route('/buscar', methods=['GET', 'POST'])
def buscar():
    if request.method == 'POST':
        query = request.form['query']
        tipo_busqueda = request.form.get('tipo_busqueda', 'titulo')
        
        if tipo_busqueda == 'titulo':
            datos_titulo = buscar_libros_por_titulo(API_KEY, query)
            if "items" in datos_titulo:
                libros_titulo = [libro for libro in datos_titulo["items"] if "imageLinks" in libro["volumeInfo"]]
                agregar_a_ultimos_libros(libros_titulo[:5])
                if len(libros_titulo) == 1:
                    libro = libros_titulo[0]
                    libro['volumeInfo']['description'] = eliminar_etiquetas_html(libro['volumeInfo'].get('description', ''))
                    return render_template('detalle_libro.html', libro=libro)
                return render_template('lista_libros.html', libros=libros_titulo, query=query, tipo_busqueda='titulo')
        
        elif tipo_busqueda == 'autor':
            agregar_a_ultimos_autores(query)
            return redirect(url_for('detalle_autor', autor=query))
    
    return render_template('index.html')

@app.route('/detalle_autor/<autor>')
def detalle_autor(autor):
    info_autor = obtener_info_autor(API_KEY, autor)
    descripcion_autor = info_autor['descripcion']
    imagen_autor = info_autor['imagen']
    libros_autor = info_autor['libros']
    return render_template('detalle_autor.html', autor=autor, descripcion=descripcion_autor, imagen=imagen_autor, libros=libros_autor)

@app.route('/detalle_libro/<id>')
def detalle_libro(id):
    url = f"https://www.googleapis.com/books/v1/volumes/{id}?key={API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        libro = response.json()
        isbn = libro["volumeInfo"].get("industryIdentifiers", [{}])[0].get("identifier", "No disponible")
        generos = ", ".join(libro["volumeInfo"].get("categories", ["No disponible"]))
        edad_recomendada = clasificar_edad(libro["volumeInfo"].get("maturityRating", "No especificado"))
        precio_fisico = "20.00 €"
        precio_kindle = "10.00 €"
        libro['volumeInfo']['description'] = eliminar_etiquetas_html(libro['volumeInfo'].get('description', ''))
        return render_template('detalle_libro.html', libro=libro, isbn=isbn, generos=generos, edad_recomendada=edad_recomendada, precio_fisico=precio_fisico, precio_kindle=precio_kindle)
    else:
        error = response.json()
        return render_template('index.html', error=error)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
