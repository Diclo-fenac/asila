import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { loginSchema, type LoginFormData } from '../../utils/validators'
import { Input } from '../../components/ui/Input'
import { Button } from '../../components/ui/Button'
import { TenantSelector } from './TenantSelector'
import { Footer } from '../../components/Footer'

export function LoginForm() {
  const { login, isLoading } = useAuth()
  const [serverError, setServerError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: '',
      password: '',
    },
  })

  const [tenantId, setTenantId] = useState('global')

  const onSubmit = async (data: LoginFormData) => {
    setServerError(null)
    const result = await login({ ...data, tenant_id: tenantId })

    if (!result.success) {
      setServerError(result.error)
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-aasila-bg-main text-aasila-text">
      <main className="relative flex flex-grow items-center justify-center p-6">
        {/* Background Architectural Motif */}
        <div className="pointer-events-none absolute inset-0 z-0 overflow-hidden opacity-5">
          <div
            className="absolute left-0 top-0 h-full w-full"
            style={{
              backgroundImage: 'radial-gradient(circle at 2px 2px, var(--color-aasila-text) 1px, transparent 0)',
              backgroundSize: '40px 40px',
            }}
          />
        </div>

        {/* Auth Card */}
        <div className="relative z-10 w-full max-w-[420px] overflow-hidden rounded-lg border border-aasila-border/30 bg-aasila-surface-ai">
          {/* Branding Header */}
          <div className="p-8 pb-4">
            <div className="mb-8 flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-sm bg-emerald-500">
                <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <span className="text-xl font-bold uppercase tracking-tighter">Aasila</span>
            </div>
            <h1 className="text-lg font-semibold">System Authentication</h1>
            <p className="font-mono text-[12px] uppercase tracking-wider text-aasila-muted">
              Access Level: Secure Terminal v2.4.0
            </p>
          </div>

          <div className="px-8 pb-10">
            {serverError && (
              <div className="mb-5 rounded-md border border-red-500/30 bg-red-500/5 p-3 text-sm text-red-500" role="alert">
                {serverError}
              </div>
            )}

            <form className="space-y-5" onSubmit={handleSubmit(onSubmit)} noValidate>
              {/* Tenant Selector */}
              <TenantSelector value={tenantId} onChange={setTenantId} />

              {/* Email Field */}
              <Input
                id="email"
                type="email"
                label="Identifier (Email)"
                placeholder="operator@aasila.systems"
                autoComplete="email"
                aria-required="true"
                {...register('email')}
                error={errors.email?.message}
              />

              {/* Password Field */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label
                    htmlFor="password"
                    className="text-[11px] font-medium uppercase tracking-wider text-aasila-muted"
                  >
                    Security Key
                  </label>
                  <a href="#" className="text-[10px] uppercase text-emerald-500 hover:underline">
                    Recovery
                  </a>
                </div>
                <Input
                  id="password"
                  type="password"
                  label=""
                  placeholder="••••••••••••"
                  autoComplete="current-password"
                  aria-required="true"
                  {...register('password')}
                  error={errors.password?.message}
                />
              </div>

              {/* Submit Button */}
              <Button
                type="submit"
                className="mt-8 w-full"
                isLoading={isLoading}
              >
                <span className="uppercase tracking-widest">Initialize Access</span>
                <svg className="h-[18px] w-[18px] text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              </Button>
            </form>

            {/* Navigation */}
            <div className="mt-6 text-center">
              <p className="text-[13px] text-aasila-muted">
                New operative?{' '}
                <Link
                  to="/signup"
                  className="font-semibold text-aasila-text underline decoration-emerald-500/30 underline-offset-4 transition-colors hover:text-emerald-500"
                >
                  Sign Up
                </Link>
              </p>
            </div>

            {/* Help Links */}
            <div className="mt-8 flex items-center justify-between border-t border-aasila-border/20 pt-6">
              <div className="flex gap-4">
                <span
                  className="cursor-help text-aasila-muted"
                  title="Hardware Token Required"
                >
                  <svg className="h-[18px] w-[18px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                  </svg>
                </span>
                <span
                  className="cursor-help text-aasila-muted"
                  title="IP Filtering Active"
                >
                  <svg className="h-[18px] w-[18px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.14 0M1.394 9.393c5.857-5.858 15.355-5.858 21.213 0" />
                  </svg>
                </span>
              </div>
              <p className="font-mono text-[10px] uppercase tracking-tighter text-aasila-muted">
                Status: [ ONLINE ]
              </p>
            </div>
          </div>
        </div>

        {/* Decorative UI Element */}
        <div className="absolute right-12 bottom-12 hidden text-right opacity-10 lg:block">
          <div className="font-mono text-[8px] leading-relaxed uppercase tracking-[0.2em]">
            System_Check: PASS
            <br />
            Encryption: AES-256-GCM
            <br />
            Identity_Protocol: OIDC_SECURE
            <br />
            Session_TTL: 43200s
          </div>
        </div>
      </main>
      <Footer />
    </div>
  )
}
