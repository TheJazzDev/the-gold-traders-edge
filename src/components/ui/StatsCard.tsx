"use client";

import { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface StatsCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: ReactNode;
  trend?: "up" | "down" | "neutral";
  className?: string;
}

export function StatsCard({
  title,
  value,
  subtitle,
  icon,
  trend,
  className,
}: StatsCardProps) {
  return (
    <div className={cn("glass-card p-5", className)}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-secondary-400 mb-1">{title}</p>
          <p
            className={cn(
              "text-2xl font-bold",
              trend === "up" && "text-profit",
              trend === "down" && "text-loss",
              !trend && "text-white"
            )}
          >
            {value}
          </p>
          {subtitle && (
            <p className="text-xs text-secondary-500 mt-1">{subtitle}</p>
          )}
        </div>
        {icon && (
          <div className="p-2 rounded-lg bg-secondary-800/50">{icon}</div>
        )}
      </div>
    </div>
  );
}
