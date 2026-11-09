-- Add result_type and is_walkover columns to match table for extensible outcome tracking
ALTER TABLE `match`
ADD COLUMN `result_type` VARCHAR(20) NOT NULL DEFAULT 'regular',
ADD COLUMN `is_walkover` TINYINT(1) NOT NULL DEFAULT 0;
