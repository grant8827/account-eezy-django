-- SQL script to manually add the user_id column if it doesn't exist
-- This can be run directly in the PostgreSQL database

-- Check if the column exists and add it if it doesn't
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'employees_employee' AND column_name = 'user_id'
    ) THEN
        -- Add the user_id column
        ALTER TABLE employees_employee ADD COLUMN user_id INTEGER;
        
        -- Add the foreign key constraint
        ALTER TABLE employees_employee 
        ADD CONSTRAINT employees_employee_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES auth_user(id) ON DELETE CASCADE;
        
        -- Create an index for performance
        CREATE INDEX employees_employee_user_id_idx ON employees_employee(user_id);
        
        RAISE NOTICE 'user_id column added successfully';
    ELSE
        RAISE NOTICE 'user_id column already exists';
    END IF;
END $$;