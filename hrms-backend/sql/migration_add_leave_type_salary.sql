-- ============================================================
-- HRMS 兼容迁移：新增请假类型表、薪资记录表
-- 适用于已经运行过旧版 init.sql、数据库中存在业务数据的环境。
-- 执行前请先备份数据库。本脚本按顺序执行一次即可。
-- ============================================================

USE `hrms`;
SET NAMES utf8mb4;

-- 1. 建立请假类型字典表。
CREATE TABLE IF NOT EXISTS `leave_type` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '请假类型ID',
  `code` VARCHAR(30) NOT NULL COMMENT '类型代码',
  `name` VARCHAR(50) NOT NULL COMMENT '类型名称',
  `is_paid` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否带薪',
  `max_days_per_year` DECIMAL(5, 1) DEFAULT NULL COMMENT '每年最大天数',
  `requires_approval` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否需要审批',
  `is_active` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_leave_type_code` (`code`),
  UNIQUE KEY `uk_leave_type_name` (`name`),
  KEY `idx_leave_type_active` (`is_active`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_0900_ai_ci
  COMMENT='请假类型表';

-- 2. 初始化常用类型，重复执行时更新现有字典项。
INSERT INTO `leave_type` (
  `id`,
  `code`,
  `name`,
  `is_paid`,
  `max_days_per_year`,
  `requires_approval`,
  `is_active`
) VALUES
(1, 'annual', '年假', 1, 10.0, 1, 1),
(2, 'sick', '病假', 1, 10.0, 1, 1),
(3, 'personal', '事假', 0, NULL, 1, 1),
(4, 'marriage', '婚假', 1, 10.0, 1, 1),
(5, 'maternity', '产假', 1, 98.0, 1, 1)
ON DUPLICATE KEY UPDATE
  `name` = VALUES(`name`),
  `is_paid` = VALUES(`is_paid`),
  `max_days_per_year` = VALUES(`max_days_per_year`),
  `requires_approval` = VALUES(`requires_approval`),
  `is_active` = VALUES(`is_active`);

-- 3. 给已有请假申请增加可空类型字段。
ALTER TABLE `leave_request`
  ADD COLUMN `leave_type_id` BIGINT DEFAULT NULL
  COMMENT '请假类型ID'
  AFTER `user_id`;

-- 4. 存量记录统一回填为事假，保证升级后不丢失旧申请。
UPDATE `leave_request`
SET `leave_type_id` = (
  SELECT `id`
  FROM `leave_type`
  WHERE `code` = 'personal'
  LIMIT 1
)
WHERE `leave_type_id` IS NULL;

-- 5. 回填完成后收紧为非空并建立索引、外键。
ALTER TABLE `leave_request`
  MODIFY COLUMN `leave_type_id` BIGINT NOT NULL COMMENT '请假类型ID',
  ADD KEY `idx_leave_type` (`leave_type_id`),
  ADD CONSTRAINT `fk_leave_type`
    FOREIGN KEY (`leave_type_id`)
    REFERENCES `leave_type` (`id`)
    ON UPDATE CASCADE
    ON DELETE RESTRICT;

-- 6. 建立月度薪资记录表。
CREATE TABLE IF NOT EXISTS `salary_record` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '薪资记录ID',
  `user_id` BIGINT NOT NULL COMMENT '员工ID',
  `salary_month` CHAR(7) NOT NULL COMMENT '薪资月份，格式 YYYY-MM',
  `base_salary` DECIMAL(10, 2) NOT NULL DEFAULT 0.00 COMMENT '基本工资',
  `attendance_deduction` DECIMAL(10, 2) NOT NULL DEFAULT 0.00 COMMENT '考勤扣款',
  `leave_deduction` DECIMAL(10, 2) NOT NULL DEFAULT 0.00 COMMENT '请假扣款',
  `bonus` DECIMAL(10, 2) NOT NULL DEFAULT 0.00 COMMENT '奖金',
  `social_security` DECIMAL(10, 2) NOT NULL DEFAULT 0.00 COMMENT '社保',
  `tax` DECIMAL(10, 2) NOT NULL DEFAULT 0.00 COMMENT '个人所得税',
  `actual_salary` DECIMAL(10, 2) NOT NULL DEFAULT 0.00 COMMENT '实发工资',
  `status` ENUM('draft', 'issued') NOT NULL DEFAULT 'draft' COMMENT '状态',
  `created_by` BIGINT NOT NULL COMMENT '制单经理ID',
  `issued_at` DATETIME DEFAULT NULL COMMENT '发放时间',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_salary_user_month` (`user_id`, `salary_month`),
  KEY `idx_salary_month` (`salary_month`),
  KEY `idx_salary_status` (`status`),
  KEY `idx_salary_user` (`user_id`),
  KEY `idx_salary_creator` (`created_by`),

  CONSTRAINT `fk_salary_user`
    FOREIGN KEY (`user_id`)
    REFERENCES `user` (`id`)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,

  CONSTRAINT `fk_salary_creator`
    FOREIGN KEY (`created_by`)
    REFERENCES `user` (`id`)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,

  CONSTRAINT `chk_salary_actual_nonnegative`
    CHECK (`actual_salary` >= 0)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_0900_ai_ci
  COMMENT='薪资记录表';

SELECT
  '迁移完成' AS `message`,
  (SELECT COUNT(*) FROM `leave_type`) AS `leave_type_count`,
  (SELECT COUNT(*) FROM `salary_record`) AS `salary_record_count`;
