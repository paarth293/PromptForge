import React from 'react';

interface TypographyProps {
  children: React.ReactNode;
  className?: string;
}

export const Display = ({ children, className = '' }: TypographyProps) => (
  <h1 className={`text-display text-forge-text-primary font-bold ${className}`}>
    {children}
  </h1>
);

export const H1 = ({ children, className = '' }: TypographyProps) => (
  <h2 className={`text-h1 text-forge-text-primary font-semibold ${className}`}>
    {children}
  </h2>
);

export const H2 = ({ children, className = '' }: TypographyProps) => (
  <h3 className={`text-h2 text-forge-text-primary font-semibold ${className}`}>
    {children}
  </h3>
);

export const H3 = ({ children, className = '' }: TypographyProps) => (
  <h4 className={`text-h3 text-forge-text-primary font-semibold ${className}`}>
    {children}
  </h4>
);

export const Body = ({ children, className = '' }: TypographyProps) => (
  <p className={`text-body text-forge-text-secondary ${className}`}>
    {children}
  </p>
);

export const Label = ({ children, className = '' }: TypographyProps) => (
  <label className={`text-label text-forge-text-secondary font-semibold ${className}`}>
    {children}
  </label>
);

export const Caption = ({ children, className = '' }: TypographyProps) => (
  <small className={`text-caption text-forge-text-secondary ${className}`}>
    {children}
  </small>
);

export const Mono = ({ children, className = '' }: TypographyProps) => (
  <code className={`text-mono font-mono text-forge-text-primary bg-forge-cream rounded px-2 py-1 ${className}`}>
    {children}
  </code>
);

export const CostAmount = ({ children, className = '' }: TypographyProps) => (
  <span className={`text-mono font-mono font-bold text-forge-orange-rust ${className}`}>
    ${children}
  </span>
);

export const StatusBadge = ({
  children,
  status,
  className = '',
}: TypographyProps & { status: 'pass' | 'fail' | 'warning' | 'pending' }) => {
  const statusColors = {
    pass: 'bg-forge-success text-white',
    fail: 'bg-forge-critical text-white',
    warning: 'bg-forge-warning text-white',
    pending: 'bg-forge-beige text-forge-text-primary',
  };

  return (
    <span
      className={`inline-block px-3 py-1 rounded-full text-sm font-semibold ${statusColors[status]} ${className}`}
    >
      {children}
    </span>
  );
};
