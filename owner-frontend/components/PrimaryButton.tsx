"use client";

import Link from "next/link";

type ButtonVariant = "primary" | "secondary" | "approve" | "reject" | "ghost" | "warning";

const variantClasses: Record<ButtonVariant, string> = {
  primary: "bg-primary text-white hover:bg-primary-dark",
  secondary: "bg-gray-200 text-gray-800 hover:bg-gray-300",
  approve: "bg-approved text-white hover:bg-green-700",
  reject: "bg-rejected text-white hover:bg-red-700",
  ghost: "bg-transparent text-primary hover:bg-blue-50 border border-primary",
  warning: "bg-pending text-white hover:bg-orange-700",
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
