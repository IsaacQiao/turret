// facial_rec.cpp : Defines the entry point for the console application.
//

//#include "stdafx.h"
#include <opencv2/opencv.hpp>
#include <iostream>
#include <math.h>
#include <stdio.h>

using namespace std;
using namespace cv;

double face_rec(Mat reference_image, Mat test_image);
void takeDFT(Mat& src, Mat& dst);
void showDFT(Mat& src);
void recenterDFT(Mat& src);
void invertDFT(Mat& src, Mat& dst);
void Correlate2d(const Mat& src1, const Mat& src2, Mat& dst, double* psf);

int main()
{
	bool owner_found = false;
	vector<String> ref_filenames;
	vector<String> test_filenames;
	String ref_folder = "//home//pi//face_recognition//ref//*.jpg";
	String test_folder = "//home//pi//face_recognition//test//*.jpg";
	glob(ref_folder, ref_filenames);
	glob(test_folder, test_filenames);
	double PSF = 0;

	Mat img1;
	Mat img2;

	if(test_filenames.size() == 0 || ref_filenames.size() == 0)
	{
		return -2;
	}

        //printf("hello");<< endl;
	for (int i = 0; i < test_filenames.size(); ++i)
	{
		for (int j = 0; j < ref_filenames.size(); ++j)
		{
			img1 = imread(ref_filenames[j]);
			img2 = imread(test_filenames[i]);
			Mat gray_img1(img1.size(), CV_8UC1);
			Mat gray_img2(img2.size(), CV_8UC1);

			cvtColor(img1, gray_img1, CV_RGB2GRAY);
			cvtColor(img2, gray_img2, CV_RGB2GRAY);

			PSF = face_rec(gray_img1, gray_img2);

			printf("PSF %f\n",PSF);
			if (PSF > 2.8)
			{
				cout << "Found Owner" << endl;
				owner_found = true;
                                break;
			}
		}

		/*//delete file once done processing
		if (remove(test_filenames[0].c_str()) != 0)
			perror("Error deleting file");
		else
			puts("File successfully deleted");*/
		//job is done when owner is found
		if (owner_found)
		{
			break;
		}
	}

	//if owner not found
	if (!owner_found)
	{
		cout << "Intruder" << endl;
		return -1;
	}
	
    return 0;
}

//returns dft Mat object
//[0] is real
//[1] is img
void takeDFT(Mat& src, Mat& dst)
{

	//dft ready objects
	Mat DFT_rdy;
	Mat DFT_result;

	Mat result;
	//take the fourier transform
	//create 2 channel Mat object for DFT
	Mat img_complex[2] = { src, Mat::zeros(src.size(), CV_64F) };
	//merge 
	merge(img_complex, 2, DFT_rdy);
	//DFT step
	dft(DFT_rdy, DFT_result, DFT_REAL_OUTPUT);

	dst = DFT_result;
}

void invertDFT(Mat& src, Mat& dst)
{
	Mat inverse;

	dft(src, inverse, DFT_INVERSE | DFT_REAL_OUTPUT | DFT_SCALE);

	dst = inverse;
}

void showDFT(Mat& src)
{
	Mat splitArray[2] = { Mat::zeros(src.size(), CV_64F), Mat::zeros(src.size(), CV_64F) };
	//split into img and reals
	split(src, splitArray);

	Mat dftMag;

	magnitude(splitArray[0], splitArray[1], dftMag);

	dftMag += Scalar::all(1);

	log(dftMag, dftMag);

	normalize(dftMag, dftMag, 0, 1, CV_MINMAX);
	imshow("DFT", dftMag);
	waitKey(0);
}

void recenterDFT(Mat& src)
{
	int centerX = src.cols / 2;
	int centerY = src.rows / 2;

	Mat q1(src, Rect(0, 0, centerX, centerY));
	Mat q2(src, Rect(centerX, 0, centerX, centerY));
	Mat q3(src, Rect(0, centerY, centerX, centerY));
	Mat q4(src, Rect(centerX, centerY, centerX, centerY));

	Mat swapMap;

	q1.copyTo(swapMap);
	q4.copyTo(q1);
	swapMap.copyTo(q4);

	q2.copyTo(swapMap);
	q3.copyTo(q2);
	swapMap.copyTo(q3);
}


double face_rec(Mat reference_image, Mat test_image)
{
	//CV_64FC1
	double PSF = 0;
	Size size(500, 500);
	Mat im1(size, CV_8UC1);
	Mat im2(size, CV_8UC1);
	//dft object
	Mat DFT_img1;
	Mat DFT_img2;
	Mat result;

	//resize images
	resize(reference_image, im1, size);
	resize(test_image, im2, size);

	im1.convertTo(im1, CV_64F);
	im2.convertTo(im2, CV_64F);

	Correlate2d(im1, im2, result, &PSF);
	return PSF;
}


void Correlate2d(const Mat& src1, const Mat& src2, Mat& dst, double* psf)
{

	Scalar mean_val;
	double peak_val = 0;
	Scalar std_val;

	CV_Assert(src1.type() == src2.type());
	CV_Assert(src1.type() == CV_32FC1 || src1.type() == CV_64FC1);
	CV_Assert(src1.size == src2.size);

	int M = getOptimalDFTSize(src1.rows);
	int N = getOptimalDFTSize(src1.cols);

	Mat padded1, padded2, paddedWin;

	if (M != src1.rows || N != src1.cols)
	{
		copyMakeBorder(src1, padded1, 0, M - src1.rows, 0, N - src1.cols, BORDER_CONSTANT, Scalar::all(0));
		copyMakeBorder(src2, padded2, 0, M - src2.rows, 0, N - src2.cols, BORDER_CONSTANT, Scalar::all(0));
	}
	else
	{
		padded1 = src1;
		padded2 = src2;
	}

	Mat FFT1, FFT2, P, Pm, C;

	// correlation equation
	dft(padded1, FFT1, DFT_REAL_OUTPUT);
	dft(padded2, FFT2, DFT_REAL_OUTPUT);

	mulSpectrums(FFT1, FFT2, dst, 0, true);
	dft(dst, dst, DFT_INVERSE | DFT_SCALE); // gives us the correlation result...
	recenterDFT(dst); // shift the energy to the center of the frame.

	// locate the highest peak
	Point peakLoc;
	minMaxLoc(dst, NULL, NULL, NULL, &peakLoc);
	
	meanStdDev(dst, mean_val, std_val);
	//calculate psf
	*psf = (dst.at<double>(peakLoc) - mean_val[0]) / std_val[0];
}
