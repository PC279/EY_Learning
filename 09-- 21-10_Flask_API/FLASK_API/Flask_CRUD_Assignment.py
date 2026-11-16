from flask import Flask
from flask import jsonify
from flask import request

app = Flask(__name__)

students = [
    {
        "id": 1,
        "name": "Rhea Kapoor",
        "course": "Python",
        "score": 82
    },
    {
        "id": 2,
        "name": "Zain Malik",
        "course": "SQL",
        "score": 76
    },
    {
        "id": 3,
        "name": "Devika Rao",
        "course": "Cloud",
        "score": 91
    }
]

@app.route("/")
def home():
    return "<h1>Hello World!</h1>"

@app.route("/students")
def get_students():
    return jsonify(students)

@app.route("/students/<int:id>")
def get_student(id):
    for student in students:
       if student["id"] == id:
           return jsonify(student)

    return {"message": "Student not found"}, 404

@app.route("/students", methods=["POST"])
def add_student():
    # get json converts the incoming json in python dictionary
    data = request.get_json()
    students.append(data)
    return {
        "message": "Student added successfully",
        "student added": data
    }

@app.route("/students/<int:id>", methods=["PUT"])
def update_student(id):
    data = request.get_json()

    for student in students:
        if student["id"] == id:
            student["name"] = data["name"]
            student["course"] = data["course"]
            student["score"] = data["score"]

            return {
                "message": "Student updated successfully",
                "student updated": student
            }

    return {"message": "Student not found"}, 404

@app.route("/students/<int:id>", methods=["DELETE"])
def delete_student(id):

    for student in students:
        if student["id"] == id:
            students.remove(student)
            return {
                "message": "Student deleted successfully"
            }

    return {"message": "Student not found"}, 404

if __name__ == "__main__":
    app.run(debug=True)

