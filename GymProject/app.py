from flask import Flask, render_template, request, redirect, url_for, g
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
from datetime import datetime

app = Flask(__name__)

DATABASE = 'workouts.db'
EXERCISE_LIST = [
    'Squat', 'Bench Press', 'Deadlift', 'Overhead Press', 'Leg Press',
    'Bicep Curl', 'Tricep Extension', 'Lat Puldown', 'Seated Row', 'Other'
]


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()


@app.route('/', methods=['GET', 'POST'])
def index():
    db = get_db()

    if request.method == 'POST':
        date = datetime.now().strftime("%Y-%m-%d")
        exercise = request.form['exercise']
        sets = request.form['sets']
        reps = request.form['reps']
        weight = request.form['weight']
        notes = request.form['notes']

        db.execute(
            'INSERT INTO workouts (Date, Exercise, Sets, Reps, Weight, Notes) VALUES (?, ?, ?, ?, ?, ?)',
            (date, exercise, sets, reps, weight, notes)
        )
        db.commit()
        return redirect(url_for('index'))

    filter_exercise = request.args.get('filter_exercise')

    query = 'SELECT * FROM workouts'
    params = []

    if filter_exercise and filter_exercise != 'All':
        query += ' WHERE Exercise = ?'
        params.append(filter_exercise)

    query += ' ORDER BY Date DESC, id DESC'

    workouts = db.execute(query, params).fetchall()

    plot_url = create_plot(workouts, filter_exercise)

    return render_template(
        'index.html',
        workouts=workouts,
        exercises=EXERCISE_LIST,
        current_filter=filter_exercise,
        plot_url=plot_url
    )


@app.route('/delete/<int:id>')
def delete_log(id):
    db = get_db()
    db.execute('DELETE FROM workouts WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('index'))


@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_log(id):
    db = get_db()

    if request.method == 'POST':
        exercise = request.form['exercise']
        sets = request.form['sets']
        reps = request.form['reps']
        weight = request.form['weight']
        notes = request.form['notes']

        db.execute(
            'UPDATE workouts SET Exercise = ?, Sets = ?, Reps = ?, Weight = ?, Notes = ? WHERE id = ?',
            (exercise, sets, reps, weight, notes, id)
        )
        db.commit()
        return redirect(url_for('index'))

    workout = db.execute('SELECT * FROM workouts WHERE id = ?', (id,)).fetchone()

    if workout is None:
        return redirect(url_for('index'))

    return render_template(
        'edit.html',
        workout=workout,
        exercises=EXERCISE_LIST
    )


def create_plot(workouts, filter_exercise):
    if not workouts or not filter_exercise or filter_exercise == 'All':
        return None

    try:
        df = pd.DataFrame(workouts, columns=['id', 'Date', 'Exercise', 'Sets', 'Reps', 'Weight', 'Notes'])

        df['Weight'] = pd.to_numeric(df['Weight'])
        df['Date'] = pd.to_datetime(df['Date'])

        df = df.sort_values(by='Date')

        plt.figure(figsize=(10, 5))
        plt.plot(df['Date'], df['Weight'], marker='o', linestyle='-')
        plt.title(f'Progress for {filter_exercise}')
        plt.xlabel('Date')
        plt.ylabel('Weight (kg)')
        plt.grid(True)
        plt.tight_layout()

        img = io.BytesIO()
        plt.savefig(img, format='png')
        plt.close()
        img.seek(0)

        plot_url = base64.b64encode(img.getvalue()).decode('utf8')
        return f'data:image/png;base64,{plot_url}'

    except Exception as e:
        print(f"Error creating plot: {e}")
        return None


if __name__ == '__main__':
    app.run(debug=True)
