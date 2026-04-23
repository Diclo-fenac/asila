import { useState } from 'react'
import { UserInviteModal } from '../features/users/UserInviteModal'
import { RoleChangeDropdown } from '../features/users/RoleChangeDropdown'
import { useUsersList, useUpdateUserRole } from '../hooks/useUsers'
import type { UserRole } from '../types/auth'

function formatInitials(name: string): string {
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
}

function getAvatarColor(role: UserRole): string {
  switch (role) {
    case 'admin': return 'bg-emerald-500/20 text-emerald-500'
    case 'analyst': return 'bg-amber-500/20 text-amber-500'
    case 'viewer': return 'bg-slate-500/20 text-slate-500'
    default: return 'bg-slate-500/20 text-slate-500'
  }
}

export function UserManagement() {
  const [showInviteModal, setShowInviteModal] = useState(false)
  const { data, isLoading, isError } = useUsersList({ page: 1, page_size: 50 })
  const updateRoleMutation = useUpdateUserRole()

  if (isLoading) {
    return (
      <div className="mx-auto max-w-6xl p-8">
        <div className="mb-10 flex items-end justify-between border-b border-aasila-border/50 pb-6">
          <div className="space-y-2">
            <div className="h-4 w-48 animate-pulse rounded bg-aasila-border" />
            <div className="h-8 w-64 animate-pulse rounded bg-aasila-border" />
          </div>
          <div className="h-10 w-32 animate-pulse rounded bg-aasila-border" />
        </div>
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex items-center gap-4 rounded-sm border border-aasila-border bg-aasila-surface-ai p-5">
              <div className="h-10 w-10 animate-pulse rounded-sm bg-aasila-border" />
              <div className="flex-1 space-y-2">
                <div className="h-4 w-32 animate-pulse rounded bg-aasila-border" />
                <div className="h-3 w-48 animate-pulse rounded bg-aasila-border" />
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="mx-auto max-w-6xl p-8">
        <div className="rounded-md border border-red-500/30 bg-red-500/5 p-8 text-center">
          <h3 className="mb-1 text-lg font-semibold text-aasila-text">Unable to load users</h3>
          <p className="text-sm text-aasila-muted">Please try again later.</p>
        </div>
      </div>
    )
  }

  const users = data?.items ?? []
  const roleCounts = users.reduce<Record<UserRole, number>>(
    (acc, u) => {
      acc[u.role] = (acc[u.role] ?? 0) + 1
      return acc
    },
    { admin: 0, analyst: 0, viewer: 0 },
  )

  return (
    <div className="mx-auto max-w-6xl p-8">
      {/* Header */}
      <div className="mb-10 flex items-end justify-between border-b border-aasila-border/50 pb-6">
        <div>
          <h2 className="mb-2 text-[12px] font-bold uppercase tracking-[0.2em] text-emerald-500">Internal Management</h2>
          <h1 className="text-3xl font-black tracking-tight text-aasila-text">System User Directory</h1>
          <p className="mt-2 max-w-lg text-[15px] text-aasila-muted">
            Manage access levels, security clearance, and audit authentication vectors for all tenant administrators.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowInviteModal(true)}
          className="flex items-center gap-2 rounded-sm bg-emerald-500 px-6 py-2.5 text-sm font-bold tracking-tight text-white hover:bg-emerald-600 active:opacity-80"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
          </svg>
          Invite User
        </button>
      </div>

      {/* Stats */}
      <div className="mb-8 grid grid-cols-12 gap-4">
        <div className="col-span-12 flex h-40 flex-col justify-between rounded-sm border border-aasila-border/50 bg-aasila-surface-user p-6 md:col-span-4">
          <svg className="h-5 w-5 text-aasila-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
          </svg>
          <div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-aasila-muted">Active Seats</p>
            <h3 className="text-3xl font-mono font-bold text-aasila-text">{users.length}</h3>
          </div>
        </div>

        <div className="col-span-12 flex h-40 items-center justify-between rounded-sm border border-aasila-border/50 bg-aasila-surface-ai p-6 md:col-span-8">
          <div className="space-y-4">
            <p className="text-[10px] font-bold uppercase tracking-widest text-aasila-muted">Role Distribution</p>
            <div className="flex gap-8">
              {(['admin', 'analyst', 'viewer'] as UserRole[]).map((role) => (
                <div key={role}>
                  <p className="mb-1 text-xs text-aasila-muted capitalize">{role}s</p>
                  <div className="flex items-center gap-2">
                    <span className={`h-2 w-2 rounded-full ${role === 'admin' ? 'bg-emerald-500' : role === 'analyst' ? 'bg-amber-500' : 'bg-slate-400'}`} />
                    <span className="font-mono font-bold text-aasila-text">{roleCounts[role] ?? 0}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* User Table */}
      <div className="overflow-hidden rounded-sm border border-aasila-border/50 bg-aasila-surface-ai">
        <div className="flex items-center justify-between border-b border-aasila-border/50 bg-aasila-surface-user px-6 py-4">
          <span className="text-[11px] font-mono text-aasila-muted">
            Total Users: {users.length}
          </span>
        </div>

        {users.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12">
            <svg className="mb-3 h-8 w-8 text-aasila-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
            <p className="text-sm font-medium text-aasila-text">No users yet</p>
            <p className="text-xs text-aasila-muted">Invite your first user to get started.</p>
          </div>
        ) : (
          <>
            {/* Desktop table */}
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-aasila-border/50 bg-aasila-surface-ai">
                    <th scope="col" className="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-aasila-muted">User Profile</th>
                    <th scope="col" className="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-aasila-muted">Role Vector</th>
                    <th scope="col" className="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-aasila-muted">Auth Status</th>
                    <th scope="col" className="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-aasila-muted">Last Access</th>
                    <th scope="col" className="px-6 py-4" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-aasila-border/30">
                  {users.map((user) => (
                    <tr key={user.id} className="group transition-colors hover:bg-aasila-bg-main">
                      <td className="px-6 py-5">
                        <div className="flex items-center gap-4">
                          <div className={`flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-sm border border-aasila-border/50 text-sm font-bold ${getAvatarColor(user.role)}`}>
                            {formatInitials(user.name)}
                          </div>
                          <div>
                            <p className="text-[15px] font-bold text-aasila-text">{user.name}</p>
                            <p className="text-xs font-mono text-aasila-muted">{user.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-5">
                        <RoleChangeDropdown
                          userId={user.id}
                          currentRole={user.role}
                          onConfirm={(id, role) => updateRoleMutation.mutate({ userId: id, role })}
                          isLoading={updateRoleMutation.isPending}
                        />
                      </td>
                      <td className="px-6 py-5">
                        <div className="flex items-center gap-2">
                          <span className={`h-1.5 w-1.5 rounded-full ${user.mfa_enabled ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]' : 'bg-slate-400'}`} />
                          <span className="text-xs font-medium text-aasila-text">
                            {user.mfa_enabled ? 'Verified MFA' : 'MFA Pending'}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-5">
                        <p className="text-xs font-mono text-aasila-muted">
                          {user.last_login ? new Date(user.last_login).toLocaleDateString() : 'Never'}
                        </p>
                      </td>
                      <td className="px-6 py-5 text-right">
                        <button
                          type="button"
                          className="text-aasila-muted transition-colors hover:text-aasila-text"
                          aria-label={`Edit ${user.name}`}
                        >
                          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                          </svg>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile card layout */}
            <div className="space-y-3 p-4 md:hidden">
              {users.map((user) => (
                <div key={user.id} className="rounded-sm border border-aasila-border bg-aasila-surface-user p-4">
                  <div className="mb-3 flex items-center gap-3">
                    <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-sm border border-aasila-border/50 text-sm font-bold ${getAvatarColor(user.role)}`}>
                      {formatInitials(user.name)}
                    </div>
                    <div className="flex-1">
                      <p className="text-[15px] font-bold text-aasila-text">{user.name}</p>
                      <p className="text-xs font-mono text-aasila-muted">{user.email}</p>
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <RoleChangeDropdown
                        userId={user.id}
                        currentRole={user.role}
                        onConfirm={(id, role) => updateRoleMutation.mutate({ userId: id, role })}
                        isLoading={updateRoleMutation.isPending}
                      />
                      <span className={`h-1.5 w-1.5 rounded-full ${user.mfa_enabled ? 'bg-emerald-500' : 'bg-slate-400'}`} />
                      <span className="text-xs text-aasila-muted">
                        {user.mfa_enabled ? 'MFA' : 'No MFA'}
                      </span>
                    </div>
                    <span className="text-xs font-mono text-aasila-muted">
                      {user.last_login ? new Date(user.last_login).toLocaleDateString() : 'Never'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      <UserInviteModal isOpen={showInviteModal} onClose={() => setShowInviteModal(false)} />
    </div>
  )
}
