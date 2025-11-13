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
    'Bicep Curl', 'Tricep Extension', 'Lat Puldown', 'Seated Row', 'Other',
    'Dips', 'Pec Fly', 'Press Ups', 'Pull Ups', 'Row\'s', 'Rear Delt Fly'
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
        db.execute('PRAGMA foreign_keys = ON')
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

        db.execute(
            'INSERT INTO workouts (Date, Exercise, Sets, Reps, Weight) VALUES (?, ?, ?, ?, ?)',
            (date, exercise, sets, reps, weight)
        )
        db.commit()
        return redirect(url_for('index'))

    filter_exercise = request.args.get('filter_exercise')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    query = 'SELECT * FROM workouts'
    conditions = []
    params = []

    if filter_exercise and filter_exercise != 'All':
        conditions.append('Exercise = ?')
        params.append(filter_exercise)

    if date_from:
        conditions.append('Date >= ?')
        params.append(date_from)

    if date_to:
        conditions.append('Date <= ?')
        params.append(date_to)

    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)

    query += ' ORDER BY Date DESC, id DESC'

    workouts = db.execute(query, params).fetchall()

    plot_url = create_plot(workouts, filter_exercise)

    templates = db.execute('SELECT * FROM templates ORDER BY name').fetchall()

    return render_template(
        'index.html',
        workouts=workouts,
        templates=templates,
        exercises=EXERCISE_LIST,
        current_filter=filter_exercise,
        current_date_from=date_from,
        current_date_to=date_to,
        plot_url=plot_url
    )


@app.route('/load_template', methods=['POST'])
def load_template():
    template_id = request.form['template_id']
    db = get_db()

    exercises = db.execute(
        'SELECT exercise_name FROM template_exercises WHERE template_id = ?',
        (template_id,)
    ).fetchall()

    date = datetime.now().strftime("%Y-%m-%d")

    for ex in exercises:
        db.execute(
            'INSERT INTO workouts (Date, Exercise, Sets, Reps, Weight) VALUES (?, ?, 0, 0, 0)',
            (date, ex['exercise_name'])
        )

    db.commit()
    return redirect(url_for('index'))


@app.route('/records')
def records():
    db = get_db()

    distinct_exercises = db.execute(
        'SELECT DISTINCT Exercise FROM workouts ORDER BY Exercise'
    ).fetchall()

    personal_records = []
    for ex in distinct_exercises:
        exercise_name = ex['Exercise']
        pr = db.execute(
            'SELECT * FROM workouts WHERE Exercise = ? ORDER BY Weight DESC LIMIT 1',
            (exercise_name,)
        ).fetchone()
        if pr:
            personal_records.append(pr)

    return render_template('records.html', records=personal_records)


@app.route('/manage_templates', methods=['GET', 'POST'])
def manage_templates():
    db = get_db()

    if request.method == 'POST':
        if 'create_template' in request.form:
            template_name = request.form['template_name']
            if template_name:
                try:
                    db.execute('INSERT INTO templates (name) VALUES (?)', (template_name,))
                    db.commit()
                except sqlite3.IntegrityError:
                    pass

        elif 'add_exercise' in request.form:
            template_id = request.form['template_id']
            exercise_name = request.form['exercise_name']
            if template_id and exercise_name:
                db.execute(
                    'INSERT INTO template_exercises (template_id, exercise_name) VALUES (?, ?)',
                    (template_id, exercise_name)
                )
                db.commit()

        return redirect(url_for('manage_templates'))

    templates_raw = db.execute('SELECT * FROM templates ORDER BY name').fetchall()
    templates = []
    for t in templates_raw:
        exercises = db.execute(
            'SELECT * FROM template_exercises WHERE template_id = ? ORDER BY exercise_name',
            (t['id'],)
        ).fetchall()
        templates.append({'id': t['id'], 'name': t['name'], 'exercises': exercises})

    return render_template(
        'manage_templates.html',
        templates=templates,
        exercises_list=EXERCISE_LIST
    )


@app.route('/delete_template/<int:id>')
def delete_template(id):
    db = get_db()
    db.execute('DELETE FROM templates WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('manage_templates'))


@app.route('/delete_template_exercise/<int:id>')
def delete_template_exercise(id):
    db = get_db()
    db.execute('DELETE FROM template_exercises WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('manage_templates'))


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

        db.execute(
            'UPDATE workouts SET Exercise = ?, Sets = ?, Reps = ?, Weight = ? WHERE id = ?',
            (exercise, sets, reps, weight, id)
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
        df = pd.DataFrame(workouts, columns=['id', 'Date', 'Exercise', 'Sets', 'Reps', 'Weight'])

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
