"use client";

import Link from "next/link";

type ButtonVariant = "primary" | "secondary" | "approve" | "reject" | "ghost" | "warning";

const variantClasses: Record<ButtonVariant, string> = {
  primary: "bg-primary dark:bg-blue-500 text-white dark:text-white hover:bg-primary-dark dark:hover:bg-blue-600 transition-colors",
  secondary: "bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-100 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors",
  approve: "bg-approved dark:bg-green-600 text-white dark:text-white hover:bg-green-700 dark:hover:bg-green-700 transition-colors",
  reject: "bg-rejected dark:bg-red-600 text-white dark:text-white hover:bg-red-700 dark:hover:bg-red-700 transition-colors",
  ghost: "bg-transparent dark:bg-transparent text-primary dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-gray-800 border border-primary dark:border-blue-400 transition-colors",
  warning: "bg-pending dark:bg-orange-600 text-white dark:text-white hover:bg-orange-700 dark:hover:bg-orange-700 transition-colors",
};

interface PrimaryButtonProps {
  children: React.ReactNode;
  href?: string;
  type?: "button" | "submit";
  variant?: ButtonVariant;
  className?: string;
  disabled?: boolean;
  onClick?: () => void;
  icon?: React.ReactNode;
}

export function PrimaryButton({
  children,
  href,
  type = "button",
  variant = "primary",
  className = "",
  disabled,
  onClick,
  icon,
}: PrimaryButtonProps) {
  const base = "btn-large inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition-colors " + variantClasses[variant];
  const combined = `${base} ${className}`.trim();

  if (href && !disabled) {
    return (
      <Link href={href} className={combined}>
        {icon}
        {children}
      </Link>
    );
  }

  return (
    <button type={type} className={combined} disabled={disabled} onClick={onClick}>
      {icon}
      {children}
    </button>
  );
}
