CREATE TABLE IF NOT EXISTS workouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    Date TEXT NOT NULL,
    Exercise TEXT NOT NULL,
    Sets INTEGER NOT NULL,
    Reps INTEGER NOT NULL,
    Weight REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS template_exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id INTEGER NOT NULL,
    exercise_name TEXT NOT NULL,
    FOREIGN KEY (template_id) REFERENCES templates (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

INSERT OR IGNORE INTO exercises (name) VALUES
('Squat'), ('Bench Press'), ('Deadlift'), ('Overhead Press'),
('Leg Press'), ('Bicep Curl'), ('Tricep Extension'),
('Lat Pulldown'), ('Seated Row'), ('Dips'),
('Pec Fly'), ('Press Ups'), ('Pull Ups');
