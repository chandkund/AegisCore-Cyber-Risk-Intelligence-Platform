"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/components/auth/AuthProvider";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { apiFetch, createUserInvitation } from "@/lib/api";
import { Input } from "@/components/ui/Input";
import type { Paginated, UserOut } from "@/types/api";

const PAGE = 30;

export default function AdminUsersPage() {
  const { hasRole, user } = useAuth();
  const router = useRouter();
  const [data, setData] = useState<Paginated<UserOut> | null | undefined>(undefined);
  const [offset, setOffset] = useState(0);
  const [forbidden, setForbidden] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("analyst");
  const [inviteToken, setInviteToken] = useState<string | null>(null);
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [inviteLoading, setInviteLoading] = useState(false);

  const load = useCallback(async () => {
    setData(undefined);
    setForbidden(false);
    const r = await apiFetch<Paginated<UserOut>>(
      `/api/v1/users?limit=${PAGE}&offset=${offset}`,
      { method: "GET" }
    );
    if (r.status === 403) {
      setForbidden(true);
      setData(null);
      return;
    }
    if (!r.ok || !r.data) {
      setData(null);
      return;
    }
    setData(r.data);
  }, [offset]);

  useEffect(() => {
    if (!hasRole("admin")) {
      setData(null);
      setForbidden(false);
      return;
    }
    void load();
  }, [hasRole, load]);

  if (!hasRole("admin")) {
    return (
      <Card title="Access denied">
        <p className="text-slate-300">This area is restricted to administrators.</p>
        <Button type="button" className="mt-4" variant="secondary" onClick={() => router.push("/dashboard")}>
          Back to dashboard
        </Button>
      </Card>
    );
  }

  if (forbidden) {
    return (
      <Card title="Forbidden">
        <p className="text-rose-400" role="alert">
          Your session does not have admin privileges on the API (403).
        </p>
      </Card>
    );
  }

  if (data === undefined) {
    return (
      <p className="text-slate-500" role="status">
        Loading users…
      </p>
    );
  }

  if (!data) {
    return (
      <p className="text-rose-400" role="alert">
        Failed to load users.
      </p>
    );
  }

  const rows = data.items;
  const total = data.total;
  const hasPrev = offset > 0;
  const hasNext = offset + PAGE < total;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-100">Users</h2>
        <p className="mt-1 text-slate-400">
          {user?.tenant_name} ({user?.tenant_code}) admin directory ({total} users).
        </p>
      </div>

      <Card title="Invite user">
        <form
          className="grid gap-3 md:grid-cols-[1fr_180px_auto]"
          onSubmit={async (e) => {
            e.preventDefault();
            setInviteLoading(true);
            setInviteError(null);
            setInviteToken(null);
            const invite = await createUserInvitation({
              email: inviteEmail.trim(),
              role_name: inviteRole,
            });
            setInviteLoading(false);
            if (!invite) {
              setInviteError("Failed to create invitation");
              return;
            }
            setInviteToken(invite.invitation_token);
            setInviteEmail("");
          }}
        >
          <Input
            id="inviteEmail"
            name="inviteEmail"
            type="email"
            label="User email"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
            required
          />
          <label className="text-sm text-slate-300">
            Role
            <select
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-slate-100"
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value)}
            >
              <option value="analyst">analyst</option>
              <option value="manager">manager</option>
              <option value="admin">admin</option>
            </select>
          </label>
          <Button type="submit" disabled={inviteLoading} className="self-end">
            {inviteLoading ? "Inviting..." : "Create invite"}
          </Button>
        </form>
        {inviteToken ? (
          <p className="mt-3 break-all text-sm text-emerald-300">
            Invitation token (share securely): {inviteToken}
          </p>
        ) : null}
        {inviteError ? (
          <p className="mt-3 text-sm text-rose-400" role="alert">
            {inviteError}
          </p>
        ) : null}
      </Card>

      <Card title="Accounts">
        <div className="overflow-x-auto rounded-lg border border-slate-800">
          <table className="w-full min-w-[560px] text-left text-sm">
            <caption className="sr-only">User accounts</caption>
            <thead className="border-b border-slate-800 bg-slate-900/80 text-slate-400">
              <tr>
                <th scope="col" className="px-4 py-3 font-medium">
                  Email
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Name
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Roles
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Active
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {rows.map((u) => (
                <tr key={u.id}>
                  <td className="px-4 py-3 font-mono text-sky-300">{u.email}</td>
                  <td className="px-4 py-3 text-slate-200">{u.full_name}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {u.roles.map((role) => (
                        <Badge key={role} tone={role}>
                          {role}
                        </Badge>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-slate-400">{u.is_active ? "Yes" : "No"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="flex flex-wrap items-center gap-2">
        <Button
          type="button"
          variant="secondary"
          disabled={!hasPrev}
          onClick={() => setOffset((o) => Math.max(0, o - PAGE))}
        >
          Previous
        </Button>
        <Button
          type="button"
          variant="secondary"
          disabled={!hasNext}
          onClick={() => setOffset((o) => o + PAGE)}
        >
          Next
        </Button>
      </div>
    </div>
  );
}
