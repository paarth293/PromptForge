import React from 'react';

export interface CardProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
  subtitle?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
  hover?: boolean;
  onClick?: () => void;
}

export function Card({
  children,
  className = '',
  title,
  subtitle,
  icon,
  action,
  hover = true,
  onClick,
}: CardProps) {
  return (
    <div
      onClick={onClick}
      className={`
        bg-gradient-to-br from-forge-white-cream to-white border border-forge-tan-border rounded-lg p-6
        ${hover ? 'hover:border-forge-orange-rust hover:shadow-card-hover transition-all duration-300 hover:-translate-y-0.5' : ''}
        ${onClick ? 'cursor-pointer' : ''}
        ${className}
      `}
    >
      {/* Header Section */}
      {(title || icon || action) && (
        <div className="flex items-start justify-between mb-4 gap-4">
          <div className="flex items-center gap-3 flex-1 min-w-0">
            {icon && <div className="text-2xl flex-shrink-0">{icon}</div>}
            <div className="min-w-0">
              {title && <h3 className="text-h3 font-semibold text-forge-text-primary truncate">{title}</h3>}
              {subtitle && <p className="text-sm text-forge-text-secondary mt-0.5">{subtitle}</p>}
            </div>
          </div>
          {action && <div className="flex-shrink-0">{action}</div>}
        </div>
      )}

      {/* Content Section */}
      <div className="text-forge-text-secondary">{children}</div>
    </div>
  );
}

export default Card;
