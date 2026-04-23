import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { signUpSchema, getPasswordStrength, type SignUpFormData } from '../../utils/validators'
import { Input } from '../../components/ui/Input'
import { Button } from '../../components/ui/Button'
import { Footer } from '../../components/Footer'

export function SignUpForm() {
  const { signUp, isLoading } = useAuth()
  const [serverError, setServerError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<SignUpFormData>({
    resolver: zodResolver(signUpSchema),
    defaultValues: {
      name: '',
      email: '',
      password: '',
    },
  })

  const password = watch('password', '')
  const strength = getPasswordStrength(password)

  const onSubmit = async (data: SignUpFormData) => {
    setServerError(null)
    const result = await signUp({ ...data, tenant_id: 'default' })

    if (result.success) {
      setSuccess(true)
    } else {
      setServerError(result.error)
    }
  }

  if (success) {
    return (
      <div className="flex min-h-screen flex-col bg-aasila-bg-main text-aasila-text">
        <main className="flex flex-grow items-center justify-center p-6">
          <div className="w-full max-w-md rounded-lg border border-aasila-border/30 bg-aasila-surface-ai p-8 text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/10">
              <svg className="h-6 w-6 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="mb-2 text-lg font-semibold">Account Created</h2>
            <p className="mb-6 text-sm text-aasila-muted">
              Your account has been created successfully. Please sign in to continue.
            </p>
            <Link to="/login">
              <Button>Sign In</Button>
            </Link>
          </div>
        </main>
        <Footer />
      </div>
    )
  }

  return (
    <div className="flex min-h-screen flex-col bg-aasila-bg-main text-aasila-text">
      <main className="relative flex flex-grow items-center justify-center p-6">
        {/* Background */}
        <div className="pointer-events-none absolute inset-0 z-0 opacity-5">
          <div
            className="absolute inset-0"
            style={{
              backgroundImage: 'radial-gradient(var(--color-aasila-text) 0.5px, transparent 0.5px)',
              backgroundSize: '24px 24px',
            }}
          />
        </div>

        {/* Auth Card */}
        <div className="relative z-10 w-full max-w-md rounded-lg border border-aasila-border/30 bg-aasila-surface-ai p-8">
          {/* Branding */}
          <div className="mb-10 text-center">
            <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-lg bg-emerald-500">
              <svg className="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M8 11V7a4 4 0 118 0m-4 8v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2z" />
              </svg>
            </div>
            <h1 className="mb-1 text-[20px] font-bold uppercase tracking-tighter">Aasila</h1>
            <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-aasila-muted">
              Secure Enrollment Protocol
            </p>
          </div>

          {serverError && (
            <div className="mb-5 rounded-md border border-red-500/30 bg-red-500/5 p-3 text-sm text-red-500" role="alert">
              {serverError}
            </div>
          )}

          <form className="space-y-6" onSubmit={handleSubmit(onSubmit)} noValidate>
            {/* Name */}
            <Input
              id="full_name"
              label="Legal Name"
              placeholder="Johnathan Doe"
              autoComplete="name"
              {...register('name')}
              error={errors.name?.message}
            />

            {/* Email */}
            <Input
              id="username"
              label="Email Address"
              placeholder="j.doe@aasila.systems"
              type="email"
              autoComplete="email"
              {...register('email')}
              error={errors.email?.message}
            />

            {/* Password */}
            <div className="space-y-1.5">
              <Input
                id="password"
                label="Access Key"
                placeholder="••••••••••••"
                type="password"
                autoComplete="new-password"
                {...register('password')}
                error={errors.password?.message}
              />

              {/* Password Strength Meter */}
              {password && (
                <div className="pt-2">
                  <div className="mb-1 flex gap-1">
                    {[1, 2, 3, 4, 5, 6].map((i) => (
                      <div
                        key={i}
                        className={`h-1 flex-1 rounded-full transition-colors ${
                          i <= strength.score ? strength.color : 'bg-aasila-border'
                        }`}
                      />
                    ))}
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[9px] uppercase tracking-tighter text-aasila-muted">
                      Strength: {strength.label}
                    </span>
                    {strength.score >= 5 && (
                      <svg className="h-[14px] w-[14px] text-emerald-500" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z" />
                      </svg>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Submit */}
            <Button type="submit" className="mt-8 w-full" isLoading={isLoading}>
              Initialize Account
            </Button>
          </form>

          {/* Navigation */}
          <div className="mt-8 border-t border-aasila-border/20 pt-6 text-center">
            <p className="text-[13px] text-aasila-muted">
              Existing operative?{' '}
              <Link
                to="/login"
                className="font-semibold text-aasila-text underline decoration-emerald-500/30 underline-offset-4 transition-colors hover:text-emerald-500"
              >
                Sign In
              </Link>
            </p>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  )
}
