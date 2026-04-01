-- CUQuest backend
-- iteration 3
-- vincenzo lindley
-- 3-11-2026

-- enum 'only these values allowed' 
-- the database itself prevents invalid states.

Drop table if exists public.messages cascade;
Drop table if exists public.ratings cascade;
Drop table if exists public.post_images cascade;
Drop table if exists public.posts_images cascade;
Drop table if exists public.posts cascade;
Drop table if exists public.categories cascade;
Drop table if exists public.users cascade;
Drop table if exists public.schools cascade;
Drop table if exists public.domains cascade;

DROP SCHEMA IF EXISTS third_iteration CASCADE;
CREATE SCHEMA third_iteration;
SET search_path TO third_iteration;

DROP TYPE IF EXISTS request_status CASCADE;
CREATE TYPE request_status AS ENUM ('open', 'pending', 'closed', 'expired');



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

CREATE TABLE IF NOT EXISTS domains (
	domain_id SMALLSERIAL PRIMARY KEY,
	domain_name TEXT NOT NULL UNIQUE,

	constraint domains_allowed_ids_chk
		check (domain_id in (1,2,3)),

	constraint domains_allowed_values_chk
		check(lower(domain_name) in ('services','social','academic'))
);



CREATE TABLE IF NOT EXISTS categories (
	category_id BIGSERIAL PRIMARY KEY,
	name TEXT NOT NULL UNIQUE, -- prevent duplicates
	domain_id SMALLINT NOT NULL,

	constraint categories_domain_fk
		foreign key (domain_id)
		references domains(domain_id)
		on delete restrict
	
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
	expires_at TIMESTAMPTZ,

	constraint posts_creator_fk
		foreign key (creator_user_id)
		references users(user_id)
		on delete cascade,
		
	constraint posts_category_fk
		foreign key (category_id)
		references categories(category_id)
		on delete restrict,
		
	constraint posts_payout_nonnegative_check
		check (desired_payout is null or desired_payout >= 0),
		
	constraint posts_expires_after_created_chk
		check (expires_at is null or expires_at > created_at)
);


CREATE TABLE IF NOT EXISTS post_images (
	image_id BIGSERIAL PRIMARY KEY,
	post_id BIGINT NOT NULL REFERENCES posts(post_id) ON DELETE CASCADE,
	image_url TEXT NOT NULL,
	uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

	constraint post_images_post_fk
		foreign key (post_id)
		references posts(post_id)
		on delete cascade
);


CREATE TABLE IF NOT EXISTS ratings (
	rating_id BIGSERIAL PRIMARY KEY,
	post_id BIGINT NOT NULL,
	rater_user_id BIGINT NOT NULL,
	rated_user_id BIGINT NOT NULL,
	score INT NOT NULL,
	comment TEXT,
	created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

	constraint ratings_post_fk
		foreign key (post_id)
		references posts(post_id)
		on delete cascade,

	constraint ratings_rated_fk
		foreign key (rated_user_id)
		references users(user_id)
		on delete cascade,

	constraint ratings_rater_fk
		foreign key (rater_user_id)
		references users(user_id)
		on delete cascade,

	constraint ratings_score_chk
		check (score between 1 and 5),
		
	constraint ratings_not_self_chk
		check (rater_user_id <> rated_user_id)
);

CREATE TABLE IF NOT EXISTS messages (
	message_id BIGSERIAL PRIMARY KEY,
	sender_user_id	BIGINT not null,
	receiver_user_id BIGINT not null,
	request_id BIGINT not null,
	content TEXT NOT NULL,
	sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	is_read BOOLEAN NOT NULL DEFAULT FALSE,

	constraint messages_sender_fk
		foreign key (sender_user_id)
		references users(user_id)
		on delete cascade,

	constraint messages_receiver_fk
		foreign key (receiver_user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE,

    CONSTRAINT messages_request_fk
        FOREIGN KEY (request_id)
        REFERENCES posts(post_id)
        ON DELETE CASCADE,

    CONSTRAINT messages_not_self_chk
        CHECK (sender_user_id <> receiver_user_id),

    CONSTRAINT messages_content_not_blank_chk
        CHECK (LENGTH(TRIM(content)) > 0)
);




-- INDEXES FOR FILTERING

CREATE INDEX IF NOT EXISTS idx_posts_creator ON posts(creator_user_id);
CREATE INDEX IF NOT EXISTS idx_posts_category ON posts(category_id);
CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);
CREATE INDEX IF NOT EXISTS idx_categories_domain_id ON categories(domain_id);
CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_user_id);
CREATE INDEX IF NOT EXISTS idx_messages_receiver ON messages(receiver_user_id);
CREATE INDEX IF NOT EXISTS idx_ratings_rated_user ON ratings(rated_user_id);
CREATE INDEX IF NOT EXISTS idx_post_images_post_id ON post_images(post_id);


CREATE UNIQUE INDEX IF NOT EXISTS uq_ratings_post_rater
ON ratings(post_id, rater_user_id);

-- canonical domain rows
INSERT INTO domains (domain_id, domain_name) VALUES
    (1, 'services'),
    (2, 'social'),
    (3, 'academic')
ON CONFLICT (domain_id) DO NOTHING;