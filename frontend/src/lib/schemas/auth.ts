import { z } from 'zod';

export const loginSchema = z.object({
	email: z.string().email('Enter a valid email'),
	password: z.string().min(8, 'At least 8 characters')
});

export const signupSchema = z
	.object({
		email: z.string().email('Enter a valid email'),
		password: z.string().min(8, 'At least 8 characters'),
		confirm: z.string()
	})
	.refine((d) => d.password === d.confirm, {
		message: 'Passwords do not match',
		path: ['confirm']
	});

export const forgotSchema = z.object({
	email: z.string().email('Enter a valid email')
});
