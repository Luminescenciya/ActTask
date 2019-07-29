from flask import Flask, render_template, json, request, redirect, session
import pypyodbc
import sys
import io
import base64
from PIL import Image

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
cnxn = pypyodbc.connect(DRIVER='{ODBC Driver 17 for SQL Server}',
                    SERVER='tcp:DESKTOP-0GASHO2\SQLEXPRESS',
                    PORT='1433',
                    DATABASE='test',
                    UID='test2',
                    PWD='test2')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/GetActs')
def getacts():
    try:
        cursor = cnxn.cursor()
        cursor.execute("{CALL SelectAct}")
        rows = cursor.fetchall()
        acts_dict = []
        for row in rows:
            act_dict = {
                'Date': row[7],
                'Name': row[1],
                'Title':row[3],
                'Description': row[4],
                'Active': row[5],
                'Num': row[6]}
            acts_dict.append(act_dict)
        
        return json.dumps(acts_dict)
    except Exception as e:
        return render_template('error.html',error = str(e))


@app.route('/getActByNumber',methods=['POST'])
def getactbynumber():
    try:
        cursor = cnxn.cursor()
        param = [str(request.form['Num'])]
        cursor.execute("{CALL GetActByNumber (?)}", param)
        row = cursor.fetchone()
        print(row, file=sys.stderr)
        act_dict = {
            'Name': row[0],
            'Title':row[1],
            'Description': row[2],
            'Active': row[3],
            'Num': row[4]}
        print(act_dict, file=sys.stderr)
        return json.dumps(act_dict)
    except Exception as e:
        return render_template('error.html',error = str(e))


@app.route('/picture/<Num>.jpg')
def showpic(Num):
    try:
        cursor = cnxn.cursor()
        param = [str(Num)]
        cursor.execute("{CALL SelectPic (?)}", param)
        data = cursor.fetchone()
        if data[0]==None:
            return render_template('error.html',error = 'Ошибка !Изображения не существует!')
        im=Image.open(io.BytesIO(data[0]))
        output = io.BytesIO()
        im.save(output, format="JPEG")
        image = base64.b64encode(output.getvalue())
        return render_template('display.html', image = image.decode('utf8'))
    except Exception as e:
        return render_template('error.html',error = str(e))


@app.route('/deleteAct', methods=['POST'])
def deleteact():
    try:
        cursor = cnxn.cursor()
        param = [str(request.form['Num'])]
        cursor.execute("{CALL DeleteAct (?)}", param)
        cnxn.commit()
        return json.dumps({'status':'Успешно удалено'})
    except Exception as e:
        return render_template('error.html',error = str(e))


@app.route('/createAct', methods=['POST'])
def createact():
    try:
        cursor = cnxn.cursor()
        _number = request.form['inputNumber']
        cursor.execute("{CALL CheckNums (?)}", [str(_number)])
        answer = cursor.fetchone()
        if answer!=None:
            return render_template('error.html', error = 'Ошибка! \n Такой номер уже существует!')
        _name = request.form['inputName']
        _title = request.form['inputTitle']
        _description = request.form['inputDescription']
        _active = request.form.get('inputActive')
        if _active=='on':
            _active = True
        else:
            _active = False
        try:
            input_image_path = request.files['inputPicData']
            original_image = Image.open(input_image_path)
            rgb_im = original_image.convert('RGB')
            w, h = rgb_im.size
            cursor.execute("{CALL CheckWidth}")
            width = cursor.fetchone()
            if w>int(width[0]):
                max_size = (int(width[0]), h)
                rgb_im.thumbnail(max_size, Image.ANTIALIAS)
            with io.BytesIO() as output:
                rgb_im.save(output, format="JPEG")
                contents = output.getvalue()
            params = (_name, _title, _description, _active, pypyodbc.Binary(contents), _number)
            cursor.execute("{CALL addAct (?,?,?,?,?,?)}", params)
        except:
            params = (_name, _title, _description, _active, _number)
            print(params, file=sys.stderr)
            cursor.execute("{CALL addActWithoutPic (?,?,?,?,?)}", params)
        cnxn.commit()
        return redirect('/')
    except Exception as e:
        return render_template('error.html',error = str(e))

@app.route('/editAct', methods=['POST'])
def editact():
    try:
        cursor = cnxn.cursor()
        _number = request.form['editNumber']
        _name = request.form['editName']
        _title = request.form['editTitle']
        _description = request.form['editDescription']
        _active = request.form.get('editActive')
        print(_active, file=sys.stderr)
        if _active=='1':
            _active = True
        else:
            _active = False
        try:
            input_image_path = request.files['editPicData']
            original_image = Image.open(input_image_path)
            rgb_im = original_image.convert('RGB')
            w, h = rgb_im.size
            cursor.execute("{CALL CheckWidth}")
            width = cursor.fetchone()
            if w>int(width[0]):
                max_size = (int(width[0]), h)
                rgb_im.thumbnail(max_size, Image.ANTIALIAS)
            with io.BytesIO() as output:
                rgb_im.save(output, format="JPEG")
                contents = output.getvalue()
            params = (_name, _title, _description, _active, pypyodbc.Binary(contents), _number)
            cursor.execute("{CALL UpdateAct (?,?,?,?,?,?)}", params)
        except:
            contents = None
            params = (_name, _title, _description, _active, _number)
            cursor.execute("{CALL UpdateActWithoutPic (?,?,?,?,?)}", params)      
        cnxn.commit()
        return redirect('/')
    except Exception as e:
        return render_template('error.html',error = str(e))


if __name__ == "__main__":
    app.run(debug = False, port=5000)
