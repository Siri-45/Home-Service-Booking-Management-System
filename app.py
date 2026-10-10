from flask import Flask, render_template, request, redirect, session
from flask_mysqldb import MySQL

app = Flask(__name__)
app.secret_key = 'secretkey'

# ================= DATABASE CONFIG =================

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Sql@dbms4'
app.config['MYSQL_DB'] = 'home_service'

mysql = MySQL(app)

# ================= REGISTER =================

@app.route('/register', methods=['GET', 'POST'])
def register():

    cur = mysql.connection.cursor()

    # GET SERVICES
    cur.execute("SELECT * FROM services")
    services = cur.fetchall()

    if request.method == 'POST':

        role = request.form['role']

        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']

        # ================= USER REGISTER =================

        if role == 'user':

            address = request.form['address']

            cur.execute("""

                INSERT INTO customers
                (
                    name,
                    email,
                    phone,
                    address,
                    password,
                    role
                )

                VALUES(%s,%s,%s,%s,%s,%s)

            """, (

                name,
                email,
                phone,
                address,
                password,
                'user'

            ))

        # ================= PROVIDER REGISTER =================

        elif role == 'provider':

            experience = request.form['experience']

            service_ids = request.form.getlist('service_ids')

            # INSERT PROVIDER

            cur.execute("""

                INSERT INTO providers
                (
                    name,
                    email,
                    phone,
                    experience,
                    password,
                    is_seen
                )

                VALUES(%s,%s,%s,%s,%s,%s)

            """, (

                name,
                email,
                phone,
                experience,
                password,
                0

            ))

            mysql.connection.commit()

            provider_id = cur.lastrowid

            # INSERT MULTIPLE SERVICES

            for sid in service_ids:

                cur.execute("""

                    INSERT INTO provider_services
                    (
                        provider_id,
                        service_id
                    )

                    VALUES(%s,%s)

                """, (

                    provider_id,
                    sid

                ))

        mysql.connection.commit()

        return redirect('/')

    return render_template(
        'register.html',
        services=services
    )

# ================= LOGIN =================

@app.route('/', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        cur = mysql.connection.cursor()

        # ================= ADMIN / USER LOGIN =================

        if role == 'admin' or role == 'user':

            cur.execute("""

                SELECT *
                FROM customers

                WHERE email=%s
                AND password=%s
                AND role=%s

            """, (

                email,
                password,
                role

            ))

            user = cur.fetchone()

            if user:

                session['user_id'] = user[0]
                session['role'] = role

                if role == 'admin':
                    return redirect('/admin')

                return redirect('/dashboard')

        # ================= PROVIDER LOGIN =================

        elif role == 'provider':

            cur.execute("""

                SELECT *
                FROM providers

                WHERE email=%s
                AND password=%s

            """, (

                email,
                password

            ))

            provider = cur.fetchone()

            if provider:

                session['user_id'] = provider[0]
                session['role'] = 'provider'

                return redirect('/provider_dashboard')

        return "Invalid Login"

    return render_template('login.html')

# ================= USER DASHBOARD =================

@app.route('/dashboard')
def dashboard():

    if session.get('role') != 'user':
        return redirect('/')

    search = request.args.get('search', '')
    sort = request.args.get('sort', '')

    cur = mysql.connection.cursor()

    query = """

        SELECT *
        FROM services

        WHERE service_name LIKE %s

    """

    if sort == 'low':
        query += " ORDER BY price ASC "

    elif sort == 'high':
        query += " ORDER BY price DESC "

    cur.execute(query, ('%' + search + '%',))

    services = cur.fetchall()

    return render_template(
        'dashboard.html',
        services=services
    )

# ================= BOOK SERVICE =================

@app.route('/book/<int:id>', methods=['GET', 'POST'])
def book(id):

    if session.get('role') != 'user':
        return redirect('/')

    if request.method == 'POST':

        date = request.form['date']
        time_slot = request.form['time_slot']
        address = request.form['address']
        contact_number = request.form['contact_number']
        description = request.form['description']
        service_type = request.form['service_type']

        cur = mysql.connection.cursor()

        cur.execute("""

            INSERT INTO bookings
            (
                customer_id,
                service_id,
                service_date,
                time_slot,
                address,
                contact_number,
                description,
                service_type,
                status,
                payment_status
            )

            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)

        """, (

            session['user_id'],
            id,
            date,
            time_slot,
            address,
            contact_number,
            description,
            service_type,
            'Pending',
            'Pending'

        ))

        mysql.connection.commit()

        return redirect('/my_bookings')

    return render_template('book.html')

# ================= MY BOOKINGS =================

@app.route('/my_bookings')
def my_bookings():

    if session.get('role') != 'user':
        return redirect('/')

    cur = mysql.connection.cursor()

    cur.execute("""

        SELECT

            b.booking_id,
            s.service_name,
            b.service_date,
            b.time_slot,
            b.status,
            s.price,
            b.payment_status,
            p.name,
            p.phone

        FROM bookings b

        JOIN services s
        ON b.service_id = s.service_id

        LEFT JOIN providers p
        ON b.provider_id = p.id

        WHERE b.customer_id=%s

        ORDER BY b.booking_id DESC

    """, (session['user_id'],))

    bookings = cur.fetchall()

    return render_template(
        'my_bookings.html',
        bookings=bookings
    )

# ================= CANCEL BOOKING

@app.route('/cancel_booking/<int:id>')
def cancel_booking(id):

    cur = mysql.connection.cursor()

    cur.execute("""

        UPDATE bookings
        SET status='Cancelled'

        WHERE booking_id=%s

    """, (id,))

    mysql.connection.commit()

    return redirect('/my_bookings')

# ================= ADMIN DASHBOARD =================

@app.route('/admin')
def admin():

    if session.get('role') != 'admin':
        return redirect('/')

    cur = mysql.connection.cursor()

    # ================= UNSEEN PROVIDER COUNT =================

    cur.execute("""

        SELECT COUNT(*)
        FROM providers

        WHERE is_seen=0

    """)

    unseen_count = cur.fetchone()[0]

    # ================= NEW BOOKINGS =================

    cur.execute("""

    SELECT
        b.booking_id,
        c.name,
        s.service_name,
        b.service_date,
        b.time_slot,
        b.address,
        b.description,
        b.service_type,
        b.status,
        p.name

    FROM bookings b

        JOIN customers c
        ON b.customer_id=c.customer_id

        JOIN services s
        ON b.service_id=s.service_id

        LEFT JOIN providers p
        ON b.provider_id=p.id

        WHERE b.status='Pending'

    """)

    new_bookings = cur.fetchall()

    # ================= ASSIGNED BOOKINGS =================

    cur.execute("""

    SELECT
        b.booking_id,
        c.name,
        s.service_name,
        b.service_date,
        b.time_slot,
        b.address,
        b.description,
        b.service_type,
        b.status,
        p.name

    FROM bookings b

        JOIN customers c
        ON b.customer_id=c.customer_id

        JOIN services s
        ON b.service_id=s.service_id

        LEFT JOIN providers p
        ON b.provider_id=p.id

        WHERE b.status='Assigned'

    """)

    pending_bookings = cur.fetchall()

    # ================= COMPLETED BOOKINGS =================

    cur.execute("""

    SELECT
        b.booking_id,
        c.name,
        s.service_name,
        b.service_date,
        b.time_slot,
        b.address,
        b.description,
        b.service_type,
        b.status,
        p.name

    FROM bookings b

        JOIN customers c
        ON b.customer_id=c.customer_id

        JOIN services s
        ON b.service_id=s.service_id

        LEFT JOIN providers p
        ON b.provider_id=p.id

        WHERE b.status='Completed'

    """)

    completed_bookings = cur.fetchall()

    return render_template(

        'admin.html',

        new_bookings=new_bookings,
        pending_bookings=pending_bookings,
        completed_bookings=completed_bookings,
        unseen_count=unseen_count

    )


# ================= RESCHEDULE BOOKING=============
@app.route('/reschedule/<int:booking_id>', methods=['GET', 'POST'])
def reschedule(booking_id):

    if session.get('role') != 'user':
        return redirect('/')

    cur = mysql.connection.cursor()

    if request.method == 'POST':

        new_date = request.form['date']
        new_time = request.form['time_slot']

        cur.execute("""

    UPDATE bookings

    SET
        service_date=%s,
        time_slot=%s,
        provider_id=NULL,
        status='Pending'

    WHERE booking_id=%s

""", (

    new_date,
    new_time,
    booking_id

))

        mysql.connection.commit()

        return redirect('/my_bookings')

    cur.execute("""

        SELECT
            booking_id,
            service_date,
            time_slot

        FROM bookings

        WHERE booking_id=%s

    """, (booking_id,))

    booking = cur.fetchone()

    return render_template(
        'reschedule.html',
        booking=booking
    )
# ================= PROVIDERS PAGE =================

@app.route('/providers')
def providers():

    if session.get('role') != 'admin':
        return redirect('/')

    cur = mysql.connection.cursor()

    cur.execute("""

       SELECT
    p.id,
    p.name,
    p.email,
    p.phone,
    p.experience,
    IFNULL(
        GROUP_CONCAT(s.service_name SEPARATOR ', '),
        'No Service Assigned'
    ) AS services

FROM providers p

LEFT JOIN provider_services ps
ON p.id = ps.provider_id

LEFT JOIN services s
ON ps.service_id = s.service_id

GROUP BY
    p.id,
    p.name,
    p.email,
    p.phone,
    p.experience

    """)

    providers = cur.fetchall()

    # MARK ALL AS SEEN

    cur.execute("""

        UPDATE providers

        SET is_seen=1

    """)

    mysql.connection.commit()

    return render_template(
        'providers.html',
        providers=providers
    )

# ================= ASSIGN PROVIDER PAGE =================
# ================= ASSIGN PROVIDER PAGE =================

@app.route('/assign_provider_page/<int:booking_id>')
def assign_provider_page(booking_id):

    if session.get('role') != 'admin':
        return redirect('/')

    cur = mysql.connection.cursor()

    # ================= GET BOOKING DETAILS =================

    cur.execute("""

        SELECT
            service_id,
            service_date,
            time_slot

        FROM bookings

        WHERE booking_id=%s

    """, (booking_id,))

    booking = cur.fetchone()

    if not booking:
        return "Booking Not Found"

    service_id = booking[0]
    service_date = booking[1]
    time_slot = booking[2]

    # ================= GET AVAILABLE PROVIDERS =================

    cur.execute("""

        SELECT DISTINCT
            p.id,
            p.name,
            p.phone,
            p.experience

        FROM providers p

        INNER JOIN provider_services ps
        ON p.id = ps.provider_id

        WHERE ps.service_id=%s

        AND p.id NOT IN (

            SELECT provider_id

            FROM bookings

            WHERE service_date=%s
            AND time_slot=%s
            AND status='Assigned'
            AND provider_id IS NOT NULL

        )

    """, (

        service_id,
        service_date,
        time_slot

    ))

    providers = cur.fetchall()

    # ================= NO PROVIDER AVAILABLE =================

    message = ""

    if len(providers) == 0:

        message = "No providers available for this service on selected date and time."

    return render_template(

        'assign_provider.html',

        providers=providers,
        booking_id=booking_id,
        message=message

    )

# ================= ASSIGN PROVIDER =================

@app.route('/assign_provider/<int:booking_id>/<int:provider_id>')
def assign_provider(booking_id, provider_id):

    if session.get('role') != 'admin':
        return redirect('/')

    cur = mysql.connection.cursor()

    cur.execute("""

        UPDATE bookings

        SET
            provider_id=%s,
            status='Assigned'

        WHERE booking_id=%s

    """, (

        provider_id,
        booking_id

    ))

    mysql.connection.commit()

    return redirect('/admin')

# ================= ADD SERVICE =================

@app.route('/add_service', methods=['GET', 'POST'])
def add_service():

    if session.get('role') != 'admin':
        return redirect('/')

    if request.method == 'POST':

        name = request.form['name']
        description = request.form['description']
        duration = request.form['duration']
        price = request.form['price']

        cur = mysql.connection.cursor()

        cur.execute("""

            INSERT INTO services
            (
                service_name,
                description,
                duration,
                price
            )

            VALUES(%s,%s,%s,%s)

        """, (

            name,
            description,
            duration,
            price

        ))

        mysql.connection.commit()

        return redirect('/admin')

    return render_template('add_service.html')

# ================= PROVIDER DASHBOARD =================

@app.route('/provider_dashboard')
def provider_dashboard():

    if session.get('role') != 'provider':
        return redirect('/')

    provider_id = session['user_id']

    cur = mysql.connection.cursor()

    cur.execute("""

        SELECT
            b.booking_id,
            c.name,
            s.service_name,
            b.service_date,
            b.status,
            b.payment_status

        FROM bookings b

        JOIN customers c
        ON b.customer_id=c.customer_id

        JOIN services s
        ON b.service_id=s.service_id

        WHERE b.provider_id=%s

    """, (provider_id,))

    bookings = cur.fetchall()

    return render_template(
        'provider_dashboard.html',
        bookings=bookings
    )

# ================= PROVIDER COMPLETE =================

@app.route('/provider_complete/<int:id>')
def provider_complete(id):

    if session.get('role') != 'provider':
        return redirect('/')

    cur = mysql.connection.cursor()

    cur.execute("""

        SELECT payment_status
        FROM bookings

        WHERE booking_id=%s

    """, (id,))

    booking = cur.fetchone()

    if booking[0] != 'Paid':
        return "Payment Pending"

    cur.execute("""

        UPDATE bookings

        SET status='Completed'

        WHERE booking_id=%s

    """, (id,))

    mysql.connection.commit()

    return redirect('/provider_dashboard')

# ================= PAYMENT PAGE =================

@app.route('/payment/<int:id>')
def payment_page(id):

    if session.get('role') != 'user':
        return redirect('/')

    cur = mysql.connection.cursor()

    cur.execute("""

        SELECT
            b.booking_id,
            s.service_name,
            s.price,
            b.status,
            b.payment_status,
            p.name

        FROM bookings b

        JOIN services s
        ON b.service_id=s.service_id

        LEFT JOIN providers p
        ON b.provider_id=p.id

        WHERE b.booking_id=%s

    """, (id,))

    booking = cur.fetchone()

    # PAYMENT ALLOWED ONLY AFTER PROVIDER ASSIGNMENT

    if booking[3] == 'Pending':

        return """

        <h2 style='font-family:sans-serif;color:red;text-align:center;margin-top:50px;'>

            Provider not assigned yet.
            Payment can be done only after provider assignment.

        </h2>

        """

    # ALREADY PAID

    if booking[4] == 'Paid':

        return """

        <h2 style='font-family:sans-serif;color:green;text-align:center;margin-top:50px;'>

            Payment Already Completed

        </h2>

        """

    return render_template(
        'payment.html',
        booking=booking
    )

# ================= PAYMENT =================

@app.route('/pay/<int:id>', methods=['POST'])
def pay(id):

    amount = request.form['amount']
    method = request.form['method']

    cur = mysql.connection.cursor()

    cur.execute("""

        INSERT INTO payments
        (
            booking_id,
            amount,
            method
        )

        VALUES(%s,%s,%s)

    """, (

        id,
        amount,
        method

    ))

    cur.execute("""

        UPDATE bookings

        SET payment_status='Paid'

        WHERE booking_id=%s

    """, (id,))

    mysql.connection.commit()

    return redirect('/receipt/' + str(id))

# ================= RECEIPT =================

@app.route('/receipt/<int:id>')
def receipt(id):

    cur = mysql.connection.cursor()

    cur.execute("""

        SELECT
            b.booking_id,
            s.service_name,
            b.service_date,
            b.status,
            s.price,
            b.payment_status

        FROM bookings b

        JOIN services s
        ON b.service_id=s.service_id

        WHERE b.booking_id=%s

    """, (id,))

    data = cur.fetchone()

    return render_template(
        'receipt.html',
        data=data
    )

# ================= LOGOUT =================

@app.route('/logout')
def logout():

    session.clear()

    return redirect('/')

# ================= RUN APP =================

if __name__ == '__main__':
    app.run(debug=True)