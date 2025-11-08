from flask import Flask

app = Flask(__name__)

@app.route("/", methods=["GET"])
def hello():
    return "Hello, World!"


@app.route("/ruta2")
def salut():
    return "Salut, Lume!"

if __name__ == "__main__":
    app.run("0.0.0.0", debug=True)