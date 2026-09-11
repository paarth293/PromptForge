import React from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
}

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  disabled = false,
  className = '',
  ...props
}: ButtonProps) {
  const variantClasses = {
    primary:
      'bg-forge-orange-rust text-white hover:bg-forge-orange-light hover:shadow-brand-glow hover:scale-[1.02] active:scale-[0.98]',
    secondary:
      'bg-white border border-forge-tan-border text-forge-orange-rust hover:border-forge-orange-rust hover:shadow-card-hover',
    danger:
      'bg-forge-critical text-white hover:shadow-critical-glow active:scale-[0.98]',
    ghost:
      'text-forge-orange-rust hover:bg-forge-cream border border-transparent',
  };

  const sizeClasses = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-5 py-2.5 text-base',
    lg: 'px-7 py-3.5 text-lg',
  };

  return (
    <button
      className={`
        rounded-base font-semibold transition-all duration-200 inline-flex items-center justify-center gap-2
        ${variantClasses[variant]}
        ${sizeClasses[size]}
        ${isLoading ? 'opacity-70 cursor-not-allowed' : ''}
        ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
        ${!disabled && !isLoading ? 'cursor-pointer' : ''}
        ${className}
      `}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <span className="flex items-center gap-2">
          <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin inline-block" />
          {children}
        </span>
      ) : (
        children
      )}
    </button>
  );
}

export default Button;
