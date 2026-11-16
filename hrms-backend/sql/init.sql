-- ============================================================
-- 人事管理系统 HRMS 数据库初始化脚本
-- 数据库：MySQL 8.0
-- 表数量：9
-- 字符集：utf8mb4
-- ============================================================

SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS `hrms`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;

USE `hrms`;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `notice`;
DROP TABLE IF EXISTS `salary_record`;
DROP TABLE IF EXISTS `leave_request`;
DROP TABLE IF EXISTS `attendance`;
DROP TABLE IF EXISTS `leave_type`;
DROP TABLE IF EXISTS `user`;
DROP TABLE IF EXISTS `position`;
DROP TABLE IF EXISTS `department`;
DROP TABLE IF EXISTS `role`;

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
-- 1. 角色表
-- ============================================================
CREATE TABLE `role` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '角色ID',
  `code` ENUM('employee', 'manager') NOT NULL COMMENT '角色代码',
  `name` VARCHAR(50) NOT NULL COMMENT '角色名称',
  `description` TEXT DEFAULT NULL COMMENT '角色说明',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_role_code` (`code`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_0900_ai_ci
  COMMENT='角色表';

-- ============================================================
-- 2. 部门表
-- ============================================================
CREATE TABLE `department` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '部门ID',
  `name` VARCHAR(100) NOT NULL COMMENT '部门名称',
  `description` TEXT DEFAULT NULL COMMENT '部门说明',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_department_name` (`name`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_0900_ai_ci
  COMMENT='部门表';

-- ============================================================
-- 3. 职位表
-- ============================================================
CREATE TABLE `position` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '职位ID',
  `department_id` BIGINT NOT NULL COMMENT '所属部门ID',
  `name` VARCHAR(100) NOT NULL COMMENT '职位名称',
  `description` TEXT DEFAULT NULL COMMENT '职位说明',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_position_department_name` (`department_id`, `name`),
  KEY `idx_position_department` (`department_id`),

  CONSTRAINT `fk_position_department`
    FOREIGN KEY (`department_id`)
    REFERENCES `department` (`id`)
    ON UPDATE CASCADE
    ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_0900_ai_ci
  COMMENT='职位表';

-- ============================================================
-- 4. 用户表
-- employee：员工
-- manager：经理
-- ============================================================
CREATE TABLE `user` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  `username` VARCHAR(50) NOT NULL COMMENT '登录用户名',
  `password_hash` VARCHAR(255) NOT NULL COMMENT 'bcrypt 密码哈希',
  `role_id` BIGINT NOT NULL COMMENT '角色ID',
  `name` VARCHAR(50) NOT NULL COMMENT '姓名',
  `gender` VARCHAR(10) DEFAULT NULL COMMENT '性别',
  `phone` VARCHAR(20) DEFAULT NULL COMMENT '手机号',
  `email` VARCHAR(100) DEFAULT NULL COMMENT '邮箱',
  `department_id` BIGINT DEFAULT NULL COMMENT '部门ID',
  `position_id` BIGINT DEFAULT NULL COMMENT '职位ID',
  `hire_date` DATE DEFAULT NULL COMMENT '入职日期',
  `is_active` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用：1启用，0禁用',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_username` (`username`),
  KEY `idx_user_role` (`role_id`),
  KEY `idx_user_department` (`department_id`),
  KEY `idx_user_position` (`position_id`),
  KEY `idx_user_name` (`name`),
  KEY `idx_user_is_active` (`is_active`),

  CONSTRAINT `fk_user_role`
    FOREIGN KEY (`role_id`)
    REFERENCES `role` (`id`)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,

  CONSTRAINT `fk_user_department`
    FOREIGN KEY (`department_id`)
    REFERENCES `department` (`id`)
    ON UPDATE CASCADE
    ON DELETE SET NULL,

  CONSTRAINT `fk_user_position`
    FOREIGN KEY (`position_id`)
    REFERENCES `position` (`id`)
    ON UPDATE CASCADE
    ON DELETE SET NULL
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_0900_ai_ci
  COMMENT='用户表';

-- ============================================================
-- 5. 考勤表
-- 上班时间 09:00，下班时间 18:00
-- ============================================================
CREATE TABLE `attendance` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '考勤ID',
  `user_id` BIGINT NOT NULL COMMENT '用户ID',
  `date` DATE NOT NULL COMMENT '考勤日期',
  `check_in` TIME DEFAULT NULL COMMENT '上班打卡时间',
  `check_out` TIME DEFAULT NULL COMMENT '下班打卡时间',
  `status` ENUM(
    'normal',
    'late',
    'early',
    'late_early',
    'missing',
    'absent'
  ) NOT NULL DEFAULT 'missing' COMMENT '考勤状态',
  `remark` VARCHAR(255) DEFAULT NULL COMMENT '备注',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_attendance_user_date` (`user_id`, `date`),
  KEY `idx_attendance_date` (`date`),
  KEY `idx_attendance_status` (`status`),

  CONSTRAINT `fk_attendance_user`
    FOREIGN KEY (`user_id`)
    REFERENCES `user` (`id`)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_0900_ai_ci
  COMMENT='考勤记录表';

-- ============================================================
-- 6. 请假类型表
-- ============================================================
CREATE TABLE `leave_type` (
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

-- ============================================================
-- 7. 请假申请表
-- ============================================================
CREATE TABLE `leave_request` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '请假申请ID',
  `user_id` BIGINT NOT NULL COMMENT '申请人员工ID',
  `leave_type_id` BIGINT NOT NULL COMMENT '请假类型ID',
  `start_date` DATE NOT NULL COMMENT '请假开始日期',
  `end_date` DATE NOT NULL COMMENT '请假结束日期',
  `reason` TEXT NOT NULL COMMENT '请假原因',
  `status` ENUM(
    'pending',
    'approved',
    'rejected',
    'cancelled'
  ) NOT NULL DEFAULT 'pending' COMMENT '审批状态',
  `approver_id` BIGINT DEFAULT NULL COMMENT '审批经理ID',
  `approve_comment` TEXT DEFAULT NULL COMMENT '审批意见',
  `approve_time` DATETIME DEFAULT NULL COMMENT '审批时间',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '申请时间',

  PRIMARY KEY (`id`),
  KEY `idx_leave_user_status` (`user_id`, `status`),
  KEY `idx_leave_type` (`leave_type_id`),
  KEY `idx_leave_status_created` (`status`, `created_at`),
  KEY `idx_leave_dates` (`start_date`, `end_date`),

  CONSTRAINT `fk_leave_user`
    FOREIGN KEY (`user_id`)
    REFERENCES `user` (`id`)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,

  CONSTRAINT `fk_leave_approver`
    FOREIGN KEY (`approver_id`)
    REFERENCES `user` (`id`)
    ON UPDATE CASCADE
    ON DELETE SET NULL,

  CONSTRAINT `fk_leave_type`
    FOREIGN KEY (`leave_type_id`)
    REFERENCES `leave_type` (`id`)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,

  CONSTRAINT `chk_leave_date_range`
    CHECK (`end_date` >= `start_date`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_0900_ai_ci
  COMMENT='请假申请表';

-- ============================================================
-- 8. 薪资记录表
-- ============================================================
CREATE TABLE `salary_record` (
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

-- ============================================================
-- 9. 公告表
-- ============================================================
CREATE TABLE `notice` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '公告ID',
  `title` VARCHAR(200) NOT NULL COMMENT '公告标题',
  `content` TEXT NOT NULL COMMENT '公告内容',
  `author_id` BIGINT NOT NULL COMMENT '发布经理ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '发布时间',

  PRIMARY KEY (`id`),
  KEY `idx_notice_created_at` (`created_at`),

  CONSTRAINT `fk_notice_author`
    FOREIGN KEY (`author_id`)
    REFERENCES `user` (`id`)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_0900_ai_ci
  COMMENT='公告表';

-- ============================================================
-- 初始化数据
-- 所有初始账号密码均为：123456
-- ============================================================
INSERT INTO `role` (`id`, `code`, `name`, `description`) VALUES
(1, 'employee', '员工', '员工角色，只能查看和操作本人数据'),
(2, 'manager', '经理', '经理角色，可以管理全部人事业务数据');

INSERT INTO `department` (`id`, `name`, `description`) VALUES
(1, '人事部', '负责人事、考勤、请假和员工档案管理'),
(2, '技术部', '负责软件研发、测试和技术支持');

INSERT INTO `position` (`id`, `department_id`, `name`, `description`) VALUES
(1, 1, '人事经理', '负责人事管理和审批工作'),
(2, 2, '开发工程师', '负责软件系统开发工作');

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
(5, 'maternity', '产假', 1, 98.0, 1, 1);

INSERT INTO `user` (
  `id`,
  `username`,
  `password_hash`,
  `role_id`,
  `name`,
  `gender`,
  `phone`,
  `email`,
  `department_id`,
  `position_id`,
  `hire_date`,
  `is_active`
) VALUES
(
  1,
  'manager',
  '$2b$12$neWVxPbNZe8fUKDKV.g7sO9n2kBtkxzLx41MOH2ODrs8suHXn9LHi',
  2,
  '张经理',
  '男',
  '13800000001',
  'manager@hrms.local',
  1,
  1,
  '2020-01-01',
  1
),
(
  2,
  'employee',
  '$2b$12$ZFii5n59nXpTiKlfvBG2gunJP1D/L9LEmMY2FR3/huk57wSVLJN7G',
  1,
  '李员工',
  '女',
  '13800000002',
  'employee@hrms.local',
  2,
  2,
  '2025-01-02',
  1
);

SELECT
  `u`.`id`,
  `u`.`username`,
  `r`.`code` AS `role`,
  `u`.`name`,
  `d`.`name` AS `department`,
  `p`.`name` AS `position`,
  `u`.`is_active`
FROM `user` AS `u`
JOIN `role` AS `r` ON `r`.`id` = `u`.`role_id`
LEFT JOIN `department` AS `d` ON `d`.`id` = `u`.`department_id`
LEFT JOIN `position` AS `p` ON `p`.`id` = `u`.`position_id`
ORDER BY `u`.`id`;
