"use client";

import { useState, useEffect } from "react";
import { meRequest } from "@/lib/api";

interface UsePlatformOwnerReturn {
  isLoading: boolean;
  isPlatformOwner: boolean;
  error: string | null;
}

/**
 * Hook to check if the current user is a platform owner.
 * This is a simplified version that checks the user's role from the API.
 */
export function usePlatformOwner(): UsePlatformOwnerReturn {
  const [isLoading, setIsLoading] = useState(true);
  const [isPlatformOwner, setIsPlatformOwner] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function checkPlatformOwner() {
      try {
        // Use the same authenticated API path used everywhere else in the frontend.
        const user = await meRequest();
        if (!user) {
          setIsPlatformOwner(false);
          return;
        }

        const hasPlatformOwnerRole =
          user.roles?.includes("platform_owner") || user.is_platform_owner === true;
        setIsPlatformOwner(hasPlatformOwnerRole);
      } catch (err) {
        console.error("Error checking platform owner status:", err);
        setError(err instanceof Error ? err.message : "Unknown error");
        setIsPlatformOwner(false);
      } finally {
        setIsLoading(false);
      }
    }

    checkPlatformOwner();
  }, []);

  return {
    isLoading,
    isPlatformOwner,
    error,
  };
}
