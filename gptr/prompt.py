import os

from flask import (Blueprint, flash, g, render_template, send_from_directory,
                    request, redirect, url_for, abort, current_app)
from werkzeug.utils import secure_filename
from gptr.db import get_db

import re, time

bp = Blueprint('prompt', __name__)


@bp.route('/')
def index():
    db = get_db()
    prompts = db.execute(
        'SELECT id, title, body'
        ' FROM app'
        ' ORDER BY id DESC'
    ).fetchall()
    return render_template('prompts/index.html', prompts=prompts)


@bp.route('/create', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required'
        
        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'INSERT INTO app (title, body)'
                'VALUES (?, ?)',
                (title, body)
            )
            db.commit()
            return redirect(url_for('index'))
        
    return render_template('prompts/create.html')


def get_prompt(id):
    prompt = get_db().execute(
        'SELECT id, title, body'
        ' FROM app'
        ' WHERE id = ?',
        (id,)
    ).fetchone()

    if prompt is None:
        abort(404, f"Prompt id {id} does not exists")

    return prompt


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'csv'}


def get_variables(prompt):
    return \
    set([v.replace(r'${', '').replace('}', '') for v in re.findall(r'\${.*?}', prompt['body'])])


@bp.route('/<int:id>/use', methods=('GET', 'POST'))
def use_prompt(id):
    prompt = get_prompt(id)
    variables = get_variables(prompt)

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            
            print(request.form)
            time.sleep(10)
            return redirect(url_for('prompt.download_file', name=filename))
    
    return render_template('prompts/use.html', prompt=prompt, variables=variables)


@bp.route('/uploads/<name>')
def download_file(name):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], name)