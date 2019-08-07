from flask import Flask, render_template, json, request, redirect, session
import pypyodbc
import sys
import io
import base64
from PIL import Image

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
cnxn = pypyodbc.connect(DRIVER='{SQL Server}',
                    SERVER='DESKTOP-0GASHO2\SQLEXPRESS,1433',
                    DATABASE='test')

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
            im=Image.open(io.BytesIO(row[2]))
            output = io.BytesIO()
            im.save(output, format="JPEG")
            image = base64.b64encode(output.getvalue())
            if row[5]==True:
                activity='Активна'
            else:
                activity='Неактивна'
            act_dict = {
                'Id': row[0][2:-1],
                'Name': row[1],
                'Image':image.decode('utf8'),
                'Title':row[3],
                'Description': row[4],
                'Active': activity,
                'Num': int(row[6]),
                'Date': row[7]}
            acts_dict.append(act_dict)
            acts_dict=sorted(acts_dict, key = lambda i: i['Num'])
        return json.dumps(acts_dict)
    except Exception as e:
        return render_template('error.html',error = str(e))


@app.route('/getActByNumber',methods=['POST'])
def getactbynumber():
    cursor = cnxn.cursor()
    _number = request.form['Num']
    checkexsist=(_number,)
    cursor.execute("{CALL CheckExsist (?)}", checkexsist)
    data = cursor.fetchone()
    if data is None:
        return json.dumps('error')
    else:
        param = [str(request.form['Num'])]
        cursor.execute("{CALL GetActByNumber (?)}", param)
        row = cursor.fetchone()
        im=Image.open(io.BytesIO(row[5]))
        output = io.BytesIO()
        im.save(output, format="JPEG")
        image = base64.b64encode(output.getvalue())
        act_dict = {
            'Name': row[0],
            'Title':row[1],
            'Description': row[2],
            'Active': row[3],
            'Id': row[4][2:-1],
            'Picture':image.decode('utf8')}
        return json.dumps(act_dict)


@app.route('/SaveNums',methods=['POST'])
def savenums():
    cursor = cnxn.cursor()
    param =request.form['array']
    data=json.loads(param)
    Nums=[]
    Names=[]
    for i in data:
        Nums.append(int(i['Num']))
        Names.append(i['Name'].strip())
    i=0
    while i < len(Nums):
        params=(Nums[i],Names[i])
        cursor.execute("{CALL UpdateNums (?,?)}", params)
        cnxn.commit()
        i=i+1
    return redirect('/GetActs')


@app.route('/picture/<Num>.jpg')
def showpic(Num):
    try:
        cursor = cnxn.cursor()
        param = [str(Num)]
        cursor.execute("{CALL SelectPic (?)}", param)
        data = cursor.fetchone()
        if data[0]==None:
            return render_template('error.html',error = 'Ошибка! \n Изображения не существует!')
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
        param = [str(request.form['IdDel'])]
        cursor.execute("{CALL DeleteAct (?)}", param)
        cnxn.commit()
        return json.dumps({'status':'Успешно удалено'})
    except Exception as e:
        return render_template('error.html',error = str(e))


@app.route('/createAct', methods=['POST'])
def createact():
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
    input_image_path = request.files['inputPicData']
    try:
        original_image = Image.open(input_image_path)
    except Exception:
        return render_template('error.html',error = 'Ошибка! \n Выбранный фаил не является файлом изображения!')
    original_image.load() # необходимо для split через строку
    '''
    Следующие две строки созданы для создания белого фона у png, у которых фон
    отсутствует. По умолчанию он конвертирует в чёрный.
    '''
    rgb_im = Image.new('RGB', original_image.size, (255,255,255)) 
    rgb_im.paste(original_image, mask=original_image.split()[3])
    rgb_im.save('foo.jpg', 'JPEG', quality=80)
    w, h = rgb_im.size
    cursor.execute("{CALL CheckWidth}")
    width = cursor.fetchone()
    if w>int(width[0]):
        max_size = (int(width[0]), h)
        rgb_im.thumbnail(max_size, Image.ANTIALIAS)
    # Следующие три строки необходимы для преобразования Image типа в binary
    with io.BytesIO() as output:
        rgb_im.save(output, format="JPEG")
        contents = output.getvalue()
    params = (_name, _title, _description, _active, pypyodbc.Binary(contents), _number)
    cursor.execute("{CALL addAct (?,?,?,?,?,?)}", params)
    cnxn.commit()
    return redirect('/')


@app.route('/editAct', methods=['POST'])
def editact():
    cursor = cnxn.cursor()
    _number = request.form['editNumber']
    checkexsist=(_number,)
    cursor.execute("{CALL CheckExsist (?)}", checkexsist)
    data = cursor.fetchone()
    if data is None:
        return render_template('error.html',error = "Ошибка! Запрашиваемая акция была удалена")
    _name = request.form['editName']
    _title = request.form['editTitle']
    _description = request.form['editDescription']
    _active = request.form.get('editActive')
    if _active=='1':
        _active = True
    else:
        _active = False
    input_image_path = request.files['editPicData']
    if input_image_path.filename != '':
        try:
            original_image = Image.open(input_image_path)
        except Exception:
            return render_template('error.html',error = 'Ошибка! \n Выбранный фаил не является файлом изображения!')
        original_image.load()
        rgb_im = Image.new('RGB', original_image.size, (255,255,255)) 
        rgb_im.paste(original_image, mask=original_image.split()[3])
        rgb_im.save('foo.jpg', 'JPEG', quality=80)
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
    else:
        contents = None
        params = (_name, _title, _description, _active, _number)
        cursor.execute("{CALL UpdateActWithoutPic (?,?,?,?,?)}", params)      
    cnxn.commit()
    return redirect('/')


if __name__ == "__main__":
    app.run(debug = False, port=5000)
