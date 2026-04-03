-- CUQuest backend
-- iteration 1
-- vincenzo lindley
-- 2-20-26

-- enum 'only these values allowed' 
-- the database itself prevents invalid states.

DO $$
BEGIN
	IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname='request_status') THEN 
	 CREATE TYPE request_status AS ENUM ('open','pending','closed','expired');
	END IF;
END;
$$ LANGUAGE plpgsql;



CREATE TABLE IF NOT EXISTS schools(
	school_id BIGSERIAL PRIMARY KEY,
	school_name TEXT NOT NULL,
	domain TEXT NOT NULL UNIQUE 
	-- edu domain constraint is enforced in the users table
);

CREATE TABLE IF NOT EXISTS users(
	user_id BIGSERIAL PRIMARY KEY,
	email TEXT NOT NULL UNIQUE,
	password_hash TEXT NOT NULL, --dont store the password, it is safer to have a hash id for password
	first_name TEXT NOT NULL,
	last_name TEXT NOT NULL,
	created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- time zoned timestamp
	is_active BOOLEAN NOT NULL DEFAULT TRUE,

	CONSTRAINT users_email_edu_chk
		CHECK (email ~* '^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.EDU$') --regex 
		-- ~* = case insensitive regex match
		-- enforces that the email has to end in edu
);

CREATE TABLE IF NOT EXISTS categories (
	category_id BIGSERIAL PRIMARY KEY,
	name TEXT NOT NULL UNIQUE -- prevent duplicates
);


CREATE TABLE IF NOT EXISTS posts (
	post_id BIGSERIAL PRIMARY KEY,
	creator_user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE, -- references means this is a foreign key to the users table, it has to be a real user. deltes posts when account is deleted
	category_id BIGINT NOT NULL REFERENCES categories(category_id),
	title TEXT NOT NULL,
	description TEXT NOT NULL,
	desired_payout NUMERIC(10,2),
	status request_status NOT NULL DEFAULT 'open',
	created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	expires_at TIMESTAMPTZ
);


CREATE TABLE IF NOT EXISTS posts_images (
	image_id BIGSERIAL PRIMARY KEY,
	posts_id BIGINT NOT NULL REFERENCES posts(post_id) ON DELETE CASCADE,
	image_url TEXT NOT NULL,
	uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ratings (
	rating_id BIGSERIAL PRIMARY KEY,
	post_id BIGINT NOT NULL REFERENCES posts(post_id) ON DELETE CASCADE,
	rater_user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
	rated_user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
	score INT NOT NULL,
	comment TEXT,
	created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

	CONSTRAINT ratings_score_chk CHECK (score BETWEEN 1 AND 5),
	CONSTRAINT ratings_not_self_chk CHECK (rater_user_id <> rated_user_id)
);

CREATE TABLE IF NOT EXISTS messages (
	message_id BIGSERIAL PRIMARY KEY,
	sender_user_id	BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
	receiver_user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
	request_id BIGINT REFERENCES posts(post_id) ON DELETE CASCADE,
	content TEXT NOT NULL,
	sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	is_read BOOLEAN NOT NULL DEFAULT FALSE
);

-- INDEXES FOR FILTERING

CREATE INDEX IF NOT EXISTS idx_posts_creator ON posts(creator_user_id);
CREATE INDEX IF NOT EXISTS idx_posts_category ON posts(category_id);
CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);


-- Fully normalized relational database
-- Foreign key integrity
-- Cascading deletes
-- Data validation
-- Enum enforcement
-- Automatic timestamps
-- Web-app ready