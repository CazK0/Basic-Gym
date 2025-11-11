from flask import Flask, render_template, request, redirect, url_for
import csv
import os

app = Flask(__name__)

DATA_FILE = 'workouts.csv'
DATA_HEADER = ['Exercise', 'Sets', 'Reps', 'Weight']

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(DATA_HEADER)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        exercise = request.form['exercise']
        sets = request.form['sets']
        reps = request.form['reps']
        weight = request.form['weight']

        new_workout = [exercise, sets, reps, weight]

        with open(DATA_FILE, 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(new_workout)

        return redirect(url_for('index'))

    workouts = []

    with open(DATA_FILE, 'r') as file:
        reader = csv.reader(file)
        next(reader, None)
        for row in reader:
            if row:
                workouts.append(row)

    return render_template('index.html', workouts=workouts)


if __name__ == '__main__':
    app.run(debug=True)