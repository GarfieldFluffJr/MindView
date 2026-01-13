This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.

## Updates I made in my fork post-hackathon

* Disabled control operations (upload file, delete file, create patients and cases) since server memory is extremely low and cannot handle it

* Added notices for users to expect long build and load times since backend goes inactive after a while
Decided to store entire scan files in MongoDB with GridFS instead of storing locally and only storing metadata so it can persist across multiple devices, and fixed the segmentation so the user can change opacity and inspect different parts of the brain on different devices

* Optimized the timeline by reducing frames and number of voxels and compressed scan files so server can process the timeline

* Added footer with copyright with group member names, and added links to demo, devpost, and github repo

* Hosted everything on Vercel and Render, fully updated and able to deploy automatically

MindView is available live here: [https://mind-view-gamma.vercel.app/](https://mind-view-gamma.vercel.app/)
