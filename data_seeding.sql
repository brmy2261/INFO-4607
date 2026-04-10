rollback;
set search_path to third_iteration;

begin;

truncate table 
	messages, 
	ratings, 
	post_images, 
	posts, 
	categories, 
	users, 
	domains
restart identity cascade;


insert into domains (domain_id, domain_name) values
	(1,'services'),
	(2, 'social'),
	(3, 'academic')
on conflict (domain_id) do nothing;

insert into users(email, password_hash, first_name, last_name, is_active)
values
	('vincenzo@colorado.edu', 'hash_vincenzo', 'Vincenzo', 'Lindley', TRUE),
    ('maya@colorado.edu',     'hash_maya',     'Maya',     'Chen',    TRUE),
    ('jordan@colorado.edu',   'hash_jordan',   'Jordan',   'Lee',     TRUE),
    ('sofia@colorado.edu',    'hash_sofia',    'Sofia',    'Martinez',TRUE),
    ('liam@colorado.edu',     'hash_liam',     'Liam',     'Patel',   TRUE),
    ('ava@colorado.edu',      'hash_ava',      'Ava',      'Nguyen',  TRUE),
    ('noah@colorado.edu',     'hash_noah',     'Noah',     'Brown',   TRUE),
    ('emma@colorado.edu',     'hash_emma',     'Emma',     'Garcia',  FALSE);


insert into categories (name, domain_id)
values
	('moving help',1),
	('ride',1),
	('sewing',1),

	('events', 2),
	('clubs',2),
	('roommates',2),

	('study groups',3),
	('tech support',3),
	('textbooks',3),
	('class notes', 3);


insert into posts (creator_user_id, category_id, title, description, desired_payout, status, created_at, expires_at)
values
	(	
		(select user_id from users where email='vincenzo@colorado.edu'),
		(select category_id from categories where name = 'sewing'),
		'need help sewing a hole in a shirt',
		'looking for someone to help me sew a tear in my favorite shirt.',
		25.00,
		'open',
		now() - interval '2 days',
		now() + interval '5 days'
	),
	(
		(select user_id from users where email='maya@colorado.edu'),
		(select category_id from categories where name = 'moving help'),
		'couch moving',
		'need help moving a couch in my house',
		20.00,
		'pending',
		now() - interval '3 days',
		now() + interval '5 days'
	),
	(
		(select user_id from users where email='jordan@colorado.edu'),
		(select category_id from categories where name = 'events'),
		'pick up basketball',
		'looking to get a group together for a game tonight at 7 at the rec',
		null,
		'open',
		now() - interval '8 hours',
		now() + interval '1 day'
	),
	(
		(select user_id from users where email='sofia@colorado.edu'),
		(select category_id from categories where name = 'study groups'),
		'chem II',
		'looking for a few people to study chem with before the next midterm',
		null,
		'closed',
		now() - interval '3 days',
		now() + interval '7 days'
	),
	(
		(select user_id from users where email='liam@colorado.edu'),
		(select category_id from categories where name = 'textbooks'),
		'calc book for sale',
		'barely used calculus book in great condition.',
		15.00,
		'open',
		now() - interval '1 day',
		now() + interval '10 days'
	),
	(
		(select user_id from users where email='ava@colorado.edu'),
		(select category_id from categories where name = 'roommates'),
		'looking for roommate',
		'searching for a roommate for next year',
		null,
		'expired',
		now() - interval '20 days',
		now() + interval ' 2 days'
	),
	(
		(select user_id from users where email='noah@colorado.edu'),
		(select category_id from categories where name = 'tech support'),
		'laptop fan issues',
		'my laptop overheats fast and it looks like i need to have my fan cleaned.  i am looking for someone comfortable doing that work',
		50.00,
		'open',
		now() - interval '12 hours',
		now() + interval '4 days'
	),
	(
        (select user_id from users where email = 'emma@colorado.edu'),
        (select category_id from categories where name = 'class notes'),
        'need notes for missed philosophy lecture',
        'missed lecture due to illness and looking for clear notes from tuesday.',
        10.00,
        'pending',
        now() - interval '1 day',
        now() + interval '3 days'
    );


insert into post_images (post_id, image_url, uploaded_at)
values
    (
        (select post_id from posts where title = 'need help sewing a hole in a shirt'),
        'https://example.com/images/shirt_repair.jpg',
        now() - interval '2 days'
    ),
    (
        (select post_id from posts where title = 'couch moving'),
        'https://example.com/images/couch1.jpg',
        now() - interval '3 days'
    ),
    (
        (select post_id from posts where title = 'couch moving'),
        'https://example.com/images/couch2.jpg',
        now() - interval '3 days'
    ),
    (
        (select post_id from posts where title = 'calc book for sale'),
        'https://example.com/images/calc_book.jpg',
        now() - interval '20 hours'
    ),
    (
        (select post_id from posts where title = 'laptop fan issues'),
        'https://example.com/images/laptop_fan.jpg',
        now() - interval '10 hours'
    );


insert into ratings (post_id, rater_user_id, rated_user_id, score, comment, created_at)
values
    (
        (select post_id from posts where title = 'chem II'),
        (select user_id from users where email = 'vincenzo@colorado.edu'),
        (select user_id from users where email = 'sofia@colorado.edu'),
        5,
        'very helpful study session.',
        now() - interval '1 day'
    ),
    (
        (select post_id from posts where title = 'couch moving'),
        (select user_id from users where email = 'jordan@colorado.edu'),
        (select user_id from users where email = 'maya@colorado.edu'),
        4,
        'good communication and easy to work with.',
        now() - interval '12 hours'
    ),
    (
        (select post_id from posts where title = 'calc book for sale'),
        (select user_id from users where email = 'ava@colorado.edu'),
        (select user_id from users where email = 'liam@colorado.edu'),
        5,
        'book matched the description perfectly.',
        now() - interval '6 hours'
    ),
    (
        (select post_id from posts where title = 'need notes for missed philosophy lecture'),
        (select user_id from users where email = 'maya@colorado.edu'),
        (select user_id from users where email = 'emma@colorado.edu'),
        3,
        'helpful, but the response took a little while.',
        now() - interval '2 hours'
    );


insert into messages (sender_user_id, receiver_user_id, request_id, content, sent_at, is_read)
values
    (
        (select user_id from users where email = 'maya@colorado.edu'),
        (select user_id from users where email = 'vincenzo@colorado.edu'),
        (select post_id from posts where title = 'need help sewing a hole in a shirt'),
        'hey, i might be able to help with that. how big is the tear?',
        now() - interval '20 hours',
        true
    ),
    (
        (select user_id from users where email = 'vincenzo@colorado.edu'),
        (select user_id from users where email = 'maya@colorado.edu'),
        (select post_id from posts where title = 'need help sewing a hole in a shirt'),
        'it is pretty small, just near the bottom seam.',
        now() - interval '18 hours',
        true
    ),
    (
        (select user_id from users where email = 'jordan@colorado.edu'),
        (select user_id from users where email = 'maya@colorado.edu'),
        (select post_id from posts where title = 'couch moving'),
        'i have a truck and can help later this afternoon.',
        now() - interval '30 hours',
        false
    ),
    (
        (select user_id from users where email = 'noah@colorado.edu'),
        (select user_id from users where email = 'ava@colorado.edu'),
        (select post_id from posts where title = 'looking for roommate'),
        'is this still available?',
        now() - interval '3 days',
        false
    ),
    (
        (select user_id from users where email = 'liam@colorado.edu'),
        (select user_id from users where email = 'emma@colorado.edu'),
        (select post_id from posts where title = 'need notes for missed philosophy lecture'),
        'i have notes from tuesday if you still need them.',
        now() - interval '15 hours',
        false
    ),
    (
        (select user_id from users where email = 'sofia@colorado.edu'),
        (select user_id from users where email = 'jordan@colorado.edu'),
        (select post_id from posts where title = 'pick up basketball'),
        'i am down. how many people do you have so far?',
        now() - interval '4 hours',
        true
    );
