import { redirect } from "next/navigation";

type ApplyPageProps = {
  params: Promise<{ id: string }>;
};

export default async function ApplyPage({ params }: ApplyPageProps) {
  const { id } = await params;
  redirect(`/jobs/${id}`);
}
