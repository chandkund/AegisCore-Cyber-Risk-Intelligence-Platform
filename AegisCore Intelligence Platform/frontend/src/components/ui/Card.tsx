import { cn } from "@/lib/utils";
import type { ReactNode, HTMLAttributes } from "react";

// Main Card component (with optional title for backward compatibility)
interface CardProps extends Omit<HTMLAttributes<HTMLDivElement>, 'title'> {
  title?: string | ReactNode;
}

export function Card({
  children,
  className,
  title,
  ...props
}: CardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border border-slate-700/50 bg-slate-800/50 backdrop-blur-sm shadow-lg shadow-black/20",
        "hover:border-slate-600/50 transition-all duration-200",
        className
      )}
      {...props}
    >
      {title ? (
        <div className="border-b border-slate-700/50 px-6 py-4">
          {typeof title === "string" ? (
            <h2 className="text-lg font-semibold text-slate-100">{title}</h2>
          ) : (
            title
          )}
        </div>
      ) : null}
      <div className={title ? "p-6" : "px-6 py-4"}>
        {children}
      </div>
    </div>
  );
}

// Card Header
export function CardHeader({
  children,
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("flex flex-col space-y-1.5 p-6", className)}
      {...props}
    >
      {children}
    </div>
  );
}

// Card Title
export function CardTitle({
  children,
  className,
  ...props
}: HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3
      className={cn(
        "text-2xl font-semibold leading-none tracking-tight",
        className
      )}
      {...props}
    >
      {children}
    </h3>
  );
}

// Card Description
export function CardDescription({
  children,
  className,
  ...props
}: HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p
      className={cn("text-sm text-muted-foreground", className)}
      {...props}
    >
      {children}
    </p>
  );
}

// Card Content
export function CardContent({
  children,
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("p-6 pt-0", className)} {...props}>
      {children}
    </div>
  );
}

// Card Footer (optional, for completeness)
export function CardFooter({
  children,
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("flex items-center p-6 pt-0", className)}
      {...props}
    >
      {children}
    </div>
  );
}
