const { Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType } = require('docx');
const fs = require('fs');

const doc = new Document({
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
      }
    },
    children: [
      new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "言传身教，润物无声", bold: true, size: 44 })]
      }),
      new Paragraph({ children: [new TextRun({ text: "", size: 22 })] }),
      new Paragraph({
        children: [new TextRun({ text: "古人云：“师者，传道授业解惑也。”教师不仅是知识的传授者，更是学生品格的塑造者。在教育的道路上，真正的育人方式不仅仅是口头上的教导，更在于教师自身的一言一行。正所谓“言传身教，润物无声”，教师的影响力往往体现在那些看似微不足道的细节之中。", size: 22 })]
      }),
      new Paragraph({ children: [new TextRun({ text: "", size: 22 })] }),
      new Paragraph({
        children: [new TextRun({ text: "言传，是教师用语言去传递知识和道理。教师通过讲授、解释、引导，将抽象的知识具体化，将复杂的道理简单化。一个善于言传的教师，能够用生动的语言激发学生的学习兴趣，用循循善诱的方式引导学生深入思考。言传是教育的基础，是教师履行岗位职责的基本方式。然而，仅有言传是远远不够的。正如孔子所言：“其身正，不令而行；其身不正，虽令不从。”教师如果只说不做，言行不一，那么即使说得再有道理，也难以让学生信服。", size: 22 })]
      }),
      new Paragraph({ children: [new TextRun({ text: "", size: 22 })] }),
      new Paragraph({
        children: [new TextRun({ text: "身教，是教师用自己的实际行动去影响和感化学生。教师的每一个举动，都可能成为学生模仿的对象。当你要求学生遵守纪律时，自己是否做到了按时上课、不迟到不早退？当你教育学生要诚实守信时，自己是否做到了言行一致、说到做到？当你引导学生要热爱学习时，自己是否也在不断充电、提升自我？身教重于言教，这不仅是一句古训，更是教育的真谛。一个具有良好师德的教师，会在不经意间向学生传递正能量，这种影响是深远而持久的。", size: 22 })]
      }),
      new Paragraph({ children: [new TextRun({ text: "", size: 22 })] }),
      new Paragraph({
        children: [new TextRun({ text: "润物无声，是教育的最高境界。就像春雨滋润大地一样，良好的教育应该是在潜移默化中完成的。学生在学校不仅学习知识，更在无形中受到教师人格魅力的熏陶。这种影响不像课堂教学那样立竿见影，却能在学生的心中生根发芽，影响他们的一生。许多年后，学生可能忘记了老师教的具体知识，但老师当年对待工作的态度、对待学生的爱心、面对困难时的坚韧，却会深深印在他们的脑海中。", size: 22 })]
      }),
      new Paragraph({ children: [new TextRun({ text: "", size: 22 })] }),
      new Paragraph({
        children: [new TextRun({ text: "在当今社会，教师更应该注重言传身教。随着信息技术的快速发展，学生获取知识的渠道越来越多，教师作为知识唯一来源的地位受到了挑战。在这种情况下，教师就更应该发挥自身独特的人格魅力，用自己的专业素养、敬业精神、仁爱之心去影响学生。一个深受学生爱戴的教师，不是因为他教了多少知识，而是因为他教会了学生如何做人。", size: 22 })]
      }),
      new Paragraph({ children: [new TextRun({ text: "", size: 22 })] }),
      new Paragraph({
        children: [new TextRun({ text: "教育是一项需要用心去经营的事业。教师对学生的影响，是任何先进技术都无法替代的。让我们铭记“言传身教，润物无声”的教育理念，用我们的言行去影响每一个学生，让他们在成长的道路上不仅获得知识，更获得品格的力量。相信只要每一位教师都能做到言传身教，我们的教育事业必将迎来更加美好的明天。", size: 22 })]
      }),
      new Paragraph({ children: [new TextRun({ text: "", size: 22 })] }),
      new Paragraph({
        alignment: AlignmentType.RIGHT,
        children: [new TextRun({ text: "——致伟大的教师们", size: 22 })]
      })
    ]
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("I:/.claude email/作文_言传身教.docx", buffer);
  console.log("Word document created successfully!");
});
