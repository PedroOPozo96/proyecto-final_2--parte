from flask import Flask, render_template, request, redirect, url_for
import requests
import os
from dotenv import load_dotenv

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

app = Flask(__name__)

# Obtener la clave API desde la variable de entorno
API_KEY = os.getenv('GOOGLE_BOOKS_API_KEY')

# Listas para almacenar los últimos libros y autores buscados
ultimos_libros = []
ultimos_autores = []

# Tamaño máximo de las listas de últimos buscados
MAX_ULTIMOS_LIBROS = 5
MAX_ULTIMOS_AUTORES = 3

# Función para buscar libros por autor
def buscar_libros_por_autor(api_key, autor, start_index=0, max_results=20):
    url = f"https://www.googleapis.com/books/v1/volumes?q=inauthor:{autor}&startIndex={start_index}&maxResults={max_results}&key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": response.json()}

# Función para buscar libros por título
def buscar_libros_por_titulo(api_key, titulo, max_results=20):
    url = f"https://www.googleapis.com/books/v1/volumes?q=intitle:{titulo}&maxResults={max_results}&key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": response.json()}

# Función para agregar libros a la lista de últimos libros buscados
def agregar_a_ultimos_libros(libros):
    global ultimos_libros
    ids_existentes = {libro['id'] for libro in ultimos_libros}
    for libro in libros:
        if libro['id'] not in ids_existentes:
            ultimos_libros.insert(0, libro)
            ids_existentes.add(libro['id'])
            if len(ultimos_libros) > MAX_ULTIMOS_LIBROS:
                ultimos_libros.pop()

# Función para agregar un autor a la lista de últimos autores buscados
def agregar_a_ultimos_autores(autor):
    global ultimos_autores
    if autor not in ultimos_autores:
        ultimos_autores.insert(0, autor)
        if len(ultimos_autores) > MAX_ULTIMOS_AUTORES:
            ultimos_autores.pop()

# Función para obtener información del autor
def obtener_info_autor(api_key, autor):
    libros = buscar_libros_por_autor(api_key, autor, max_results=5)
    if "items" in libros:
        libro = libros["items"][0]
        descripcion = libro["volumeInfo"].get("description", "No se encontró una descripción del autor.")
        imagen = libro["volumeInfo"]["imageLinks"].get("thumbnail", None) if "imageLinks" in libro["volumeInfo"] else None
        return {"descripcion": descripcion, "imagen": imagen, "libros": libros["items"]}
    return {"descripcion": "No se encontró información del autor.", "imagen": None, "libros": []}

# Ruta para la página principal
@app.route('/')
def index():
    return render_template('index.html')

# Ruta para la página de búsqueda de libros
@app.route('/buscar_libros')
def buscar_libros():
    return render_template('buscar_libros.html', ultimos_libros=ultimos_libros, ultimos_autores=ultimos_autores)

# Ruta para la búsqueda
@app.route('/buscar', methods=['GET', 'POST'])
def buscar():
    if request.method == 'POST':
        query = request.form['query']
        tipo_busqueda = request.form.get('tipo_busqueda', 'titulo')
        
        if tipo_busqueda == 'titulo':
            # Buscar como título
            datos_titulo = buscar_libros_por_titulo(API_KEY, query)
            if "items" in datos_titulo:
                libros_titulo = datos_titulo["items"]
                agregar_a_ultimos_libros(libros_titulo[:5])  # Agregar los primeros 5 resultados a la lista de últimos libros buscados
                if len(libros_titulo) == 1:
                    return render_template('detalle_libro.html', libro=libros_titulo[0])
                return render_template('lista_libros.html', libros=libros_titulo, query=query, tipo_busqueda='titulo')
        
        elif tipo_busqueda == 'autor':
            # Buscar información del autor
            agregar_a_ultimos_autores(query)
            return redirect(url_for('detalle_autor', autor=query))
    
    return render_template('index.html')

# Ruta para ver el detalle de un autor
@app.route('/detalle_autor/<autor>')
def detalle_autor(autor):
    info_autor = obtener_info_autor(API_KEY, autor)
    descripcion_autor = info_autor['descripcion']
    imagen_autor = info_autor['imagen']
    libros_autor = info_autor['libros']
    return render_template('detalle_autor.html', autor=autor, descripcion=descripcion_autor, imagen=imagen_autor, libros=libros_autor)

# Ruta para ver el detalle de un libro
@app.route('/detalle_libro/<id>')
def detalle_libro(id):
    url = f"https://www.googleapis.com/books/v1/volumes/{id}?key={API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        libro = response.json()
        return render_template('detalle_libro.html', libro=libro)
    else:
        error = response.json()
        return render_template('index.html', error=error)

if __name__ == '__main__':
    app.run(debug=True)
