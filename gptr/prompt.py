import os

from flask import (Blueprint, flash, g, render_template, send_from_directory,
                    request, redirect, url_for, abort, current_app)
from werkzeug.utils import secure_filename
from gptr.db import get_db

import re, random
from . import tasks
from celery.result import AsyncResult

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
            # random int to prevent overwrites
            filename = str(random.randint(100, 999)) + '-' + secure_filename(file.filename)
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(os.path.join(filepath))

            print(filepath, prompt, variables, request.form)
            job = tasks.generate_output.delay(filepath, prompt['body'], list(variables), request.form)

            return redirect(url_for('prompt.task_result', id=job))
    
    return render_template('prompts/use.html', prompt=prompt, variables=variables)


@bp.get('/result/<id>')
def task_result(id):
    result = AsyncResult(id)
    ready = {
        "ready": result.ready(),
        "successful": result.successful(),
        "value": result.result if result.ready() else None,
    }
    return render_template('prompts/result.html', id=id)




@bp.route('/jobs/<id>')
def jobs_result(id):
    result = AsyncResult(id)
    ready = result.ready()
    return {
        "ready": ready,
        "successful": result.successful() if ready else None,
        "value": url_for("prompt.download_file", filename=result.result) if ready else result.result,
    }

@bp.get('/download/<filename>')
def download_file(filename):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)